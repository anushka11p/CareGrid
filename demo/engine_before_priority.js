// CareGrid pilot engine: a line-for-line port of caregrid/sim.py (greedy controllers only).
// tests/test_parity.py runs this file under Node and compares it to the Python results.
(function (root) {
  "use strict";
  const SETPOINT_C = 26.0, CAUTION_C = 26.7, DANGER_C = 32.2, ESSENTIAL_KW = 0.35;
  const W_CRITICAL = 10.0, W_ESSENTIAL = 2.0, W_DISCRETIONARY = 0.1;
  const NIGHT = [22, 23, 0, 1, 2, 3, 4, 5];

  const dev = (name, kw, hours) => ({ name, kw, hours: hours || [] });
  const O2 = (n) => dev(n || "oxygen concentrator", 0.35);
  function building(name, residents, devices, scale) {
    scale = scale || 1.0;
    return {
      name, residents, scale, devices: devices || [],
      R: 1.75 / scale, C: 6.0 * scale, acMaxTh: 14.0 * scale,
      solarAperture: 1.2 * scale, internalKw: 0.3 * scale + 0.1 * residents,
    };
  }
  function community() {
    return [
      building("H1", 1, [O2()]),
      building("H2", 2, [dev("CPAP", 0.06, NIGHT), dev("insulin fridge", 0.12)]),
      building("H3", 1, [O2()]),
      building("H4", 1),
      building("H5", 2, [dev("power wheelchair charger", 0.30, [22, 23, 0, 1])]),
      building("H6", 1, [dev("CPAP", 0.06, NIGHT), dev("insulin fridge", 0.12)]),
      building("H7", 1, [O2()]),
      building("H8", 2),
      building("Care facility", 6, [O2("oxygen concentrator A"), O2("oxygen concentrator B"),
        dev("ventilator", 0.15), dev("medication fridge", 0.15)], 4.0),
    ];
  }
  const active = (d, hour) => d.hours.length === 0 || d.hours.includes(hour);
  const defaultAssets = () => ({ pvKwp: 60, battKwh: 150, battKw: 60, socMin: 0.10, reserveGrid: 0.30, eta: 0.95 });

  function pvKw(a, poa, temp) {
    const tCell = temp + (45.0 - 20.0) / 800.0 * poa;
    return Math.max(0.0, a.pvKwp * poa / 1000.0 * 0.86 * (1 - 0.0035 * (tCell - 25.0)));
  }
  const cop = (temp) => Math.min(4.0, Math.max(2.0, 4.0 - 0.06 * (temp - 30.0)));
  const heatGain = (b, tin, temp, ghi) => (temp - tin) / b.R + b.solarAperture * ghi / 1000.0 + b.internalKw;
  const nextTemp = (b, tin, temp, ghi, ac) => tin + (heatGain(b, tin, temp, ghi) - cop(temp) * ac) / b.C;
  function acNeeded(b, tin, temp, ghi) {
    const q = (tin - SETPOINT_C) * b.C + heatGain(b, tin, temp, ghi);
    return Math.min(b.acMaxTh, Math.max(0.0, q)) / cop(temp);
  }
  function baseSplit(b, baseKw, hour) {
    const total = baseKw[hour] * b.scale;
    const ess = Math.min(total, ESSENTIAL_KW * b.scale);
    return [ess, total - ess];
  }
  const critDemand = (blds, hour) => blds.reduce((s, b) => s + b.devices.reduce((s2, d) => s2 + (active(d, hour) ? d.kw : 0), 0), 0);

  function runNormal(inp, a, blds, t0, t1, soc0, tin0, prechargeFrom) {
    t0 = t0 || 0; t1 = t1 == null ? inp.temp.length : t1;
    let soc = soc0 == null ? 0.5 : soc0;
    const tin = tin0 ? tin0.slice() : blds.map(() => SETPOINT_C);
    const states = {}, cap = a.battKwh;
    for (let t = t0; t < t1; t++) {
      states[t] = [soc, tin.slice()];
      const hr = inp.hour[t], temp = inp.temp[t], ghi = inp.ghi[t];
      const pv = pvKw(a, inp.poa[t], temp);
      let load = critDemand(blds, hr);
      blds.forEach((b, i) => {
        const ac = acNeeded(b, tin[i], temp, ghi);
        load += ac + inp.baseKw[hr] * b.scale;
        tin[i] = nextTemp(b, tin[i], temp, ghi, ac);
      });
      const net = load - pv;
      const pre = prechargeFrom != null && t >= prechargeFrom;
      let charge = 0, discharge = 0;
      if (net < 0) charge = Math.min(-net, a.battKw, (1 - soc) * cap / a.eta);
      else if (!pre) discharge = Math.min(net, a.battKw, Math.max(0, soc - a.reserveGrid) * cap * a.eta);
      if (pre) charge = Math.min(a.battKw, (1 - soc) * cap / a.eta);
      soc += (charge * a.eta - discharge / a.eta) / cap;
    }
    states[t1] = [soc, tin.slice()];
    return states;
  }

  function demands(inp, blds, t, tin) {
    const hr = inp.hour[t], temp = inp.temp[t], ghi = inp.ghi[t];
    return blds.map((b, i) => {
      const [ess, disc] = baseSplit(b, inp.baseKw, hr);
      const tNoac = nextTemp(b, tin[i], temp, ghi, 0.0);
      return {
        devices: b.devices.filter((d) => active(d, hr)).map((d) => d.kw),
        ess, disc, ac: acNeeded(b, tin[i], temp, ghi),
        risk: Math.max(0, tNoac - CAUTION_C) / (DANGER_C - CAUTION_C) * b.residents,
      };
    });
  }
  const pad = (i) => (i < 10 ? "0" + i : "" + i);

  function greedy(items, budget) {
    const alloc = {};
    const sorted = items.slice().sort((x, y) => (y[0] - x[0]) || (x[1] < y[1] ? -1 : x[1] > y[1] ? 1 : 0));
    for (const [, key, kw, divisible] of sorted) {
      if (kw <= budget + 1e-9) { alloc[key] = kw; budget -= kw; }
      else if (divisible && budget > 1e-9) { alloc[key] = budget; budget = 0; }
      else alloc[key] = 0;
    }
    return alloc;
  }
  function items(rows, wHeat, includeCrit) {
    const out = [];
    rows.forEach((r, i) => {
      if (includeCrit) r.devices.forEach((kw, j) => out.push([W_CRITICAL, pad(i) + "d" + j, kw, false]));
      out.push([W_ESSENTIAL, pad(i) + "e", r.ess, true]);
      out.push([wHeat * r.risk, pad(i) + "a", r.ac, true]);
      out.push([W_DISCRETIONARY, pad(i) + "x", r.disc, true]);
    });
    return out;
  }
  function unpack(rows, alloc) {
    return rows.map((r, i) => ({
      devices: r.devices.map((kw, j) => (alloc[pad(i) + "d" + j] || 0) >= kw - 1e-9),
      ess: alloc[pad(i) + "e"] || 0, ac: alloc[pad(i) + "a"] || 0, disc: alloc[pad(i) + "x"] || 0,
    }));
  }
  function critFirst(rows, supply) {
    const list = [];
    rows.forEach((r, i) => r.devices.forEach((kw, j) => list.push([kw, pad(i) + "d" + j])));
    list.sort((x, y) => (x[0] - y[0]) || (x[1] < y[1] ? -1 : 1));
    let budget = supply; const alloc = {};
    for (const [kw, key] of list) { alloc[key] = kw <= budget + 1e-9 ? kw : 0; budget -= alloc[key]; }
    return [alloc, budget];
  }

  const controllers = {
    equal(rows, ctx) {
      const demand = rows.reduce((s, r) => s + r.devices.reduce((a, b) => a + b, 0) + r.ess + r.ac + r.disc, 0);
      const f = demand <= 1e-9 ? 1 : Math.min(1, ctx.supply / demand);
      return rows.map((r) => ({ devices: r.devices.map(() => f >= 1 - 1e-9), ess: f * r.ess, ac: f * r.ac, disc: f * r.disc }));
    },
    rule(rows, ctx) {
      let [alloc, budget] = critFirst(rows, ctx.supply);
      rows.forEach((r, i) => { const e = Math.min(r.ess, budget); alloc[pad(i) + "e"] = e; budget -= e; });
      const used = ctx.supply - budget;
      const flex = ctx.soc > 0.40 ? budget : Math.max(0, Math.min(budget, ctx.pv - used));
      const want = rows.reduce((s, r) => s + r.ac + r.disc, 0);
      const f = want <= 1e-9 ? 1 : Math.min(1, flex / want);
      rows.forEach((r, i) => { alloc[pad(i) + "a"] = f * r.ac; alloc[pad(i) + "x"] = f * r.disc; });
      return unpack(rows, alloc);
    },
    soft(rows, ctx) {
      const crit = rows.reduce((s, r) => s + r.devices.reduce((a, b) => a + b, 0), 0);
      const remaining = Math.max(1, ctx.forecastEnd - ctx.t);
      const paced = Math.min(ctx.supply, ctx.pv + Math.min(ctx.battKwAvail, ctx.battKwhAvail / remaining));
      const budget = Math.max(paced, Math.min(ctx.supply, crit));
      return unpack(rows, greedy(items(rows, ctx.wHeat, true), budget));
    },
    shield(rows, ctx) {
      let [alloc, budget] = critFirst(rows, ctx.supply);
      const critUsed = ctx.supply - budget;
      const fromBatt = Math.max(0, critUsed - ctx.pv);
      const freeKwh = Math.max(0, ctx.battKwhAvail - fromBatt - ctx.reserveKwh);
      let pvLeft = Math.max(0, ctx.pv - critUsed);
      const deficit = Math.max(0, ctx.reserveKwh - (ctx.battKwhAvail - fromBatt));
      pvLeft = Math.max(0, pvLeft - Math.min(deficit / (ctx.eta * ctx.eta), ctx.battKw));
      const battKwLeft = Math.max(0, ctx.battKwAvail - fromBatt);
      const remaining = Math.max(1, ctx.forecastEnd - ctx.t);
      const nc = Math.min(budget, pvLeft + Math.min(battKwLeft, freeKwh / remaining));
      Object.assign(alloc, greedy(items(rows, ctx.wHeat, false), nc));
      return unpack(rows, alloc);
    },
  };

  function shieldReserve(inp, blds, t, p90End, pvHist) {
    const horizon = Math.max(12, p90End - t);
    let need = 0;
    const n = inp.hour.length;
    for (let k = 1; k <= horizon; k++) {
      const hr = inp.hour[(t + k) % n];
      const pvF = 0.7 * pvHist[(((t + k - 24) % n) + n) % n];
      need += Math.max(0, critDemand(blds, hr) - pvF);
    }
    return need;
  }

  function runOutage(inp, a, blds, start, duration, controller, soc0, tin0, opts) {
    opts = opts || {};
    const forecastHours = opts.forecastHours == null ? 24 : opts.forecastHours;
    const p90Hours = opts.p90Hours == null ? 48 : opts.p90Hours;
    const wHeat = opts.wHeat == null ? 1.0 : opts.wHeat;
    const ctrl = controllers[controller], cap = a.battKwh;
    let soc = soc0; const tin = tin0.slice();
    const pvHist = inp.poa.map((p, i) => pvKw(a, p, inp.temp[i]));
    const trace = [];
    for (let t = start; t < start + duration; t++) {
      const temp = inp.temp[t], ghi = inp.ghi[t], pv = pvHist[t];
      const battKwhAvail = Math.max(0, soc - a.socMin) * cap * a.eta;
      const battKwAvail = Math.min(a.battKw, battKwhAvail);
      const ctx = { t, pv, soc, battKwhAvail, battKwAvail, supply: pv + battKwAvail,
        forecastEnd: start + forecastHours, wHeat, reserveKwh: 0, eta: a.eta, battKw: a.battKw };
      if (controller === "shield") ctx.reserveKwh = shieldReserve(inp, blds, t, start + p90Hours, pvHist);
      const rows = demands(inp, blds, t, tin);
      const dec = ctrl(rows, ctx);
      let used = 0;
      const hour = { t, time: inp.time[t], tempOut: temp, pv, buildings: [] };
      blds.forEach((b, i) => {
        const r = rows[i], d = dec[i];
        const served = r.devices.reduce((s, kw, j) => s + (d.devices[j] ? kw : 0), 0);
        used += served + d.ess + d.ac + d.disc;
        hour.buildings.push({
          tin: tin[i], critDemand: r.devices.reduce((x, y) => x + y, 0), critServed: served,
          devicesDown: d.devices.filter((ok) => !ok).length,
          essUnserved: r.ess - d.ess, discUnserved: r.disc - d.disc, acUnserved: Math.max(0, r.ac - d.ac), ac: d.ac,
        });
        tin[i] = nextTemp(b, tin[i], temp, ghi, d.ac);
      });
      const net = used - pv;
      let curtailed = 0;
      if (net > 0) soc -= net / a.eta / cap;
      else {
        const charge = Math.min(-net, a.battKw, (1 - soc) * cap / a.eta);
        soc += charge * a.eta / cap;
        curtailed = -net - charge;
      }
      soc = Math.max(a.socMin - 1e-9, soc);
      Object.assign(hour, { soc, pvCurtailed: curtailed, reserveKwh: ctx.reserveKwh });
      trace.push(hour);
    }
    return trace;
  }

  function metrics(trace, blds) {
    const m = { crit_device_hours_down: 0, crit_kwh_unserved: 0, crit_kwh_demand: 0, person_hours_danger: 0,
      person_degree_hours: 0, ens_kwh: 0, hw_ens: 0, max_tin: 0, pv_curtailed_kwh: 0, hours_any_device_down: 0 };
    for (const h of trace) {
      m.pv_curtailed_kwh += h.pvCurtailed;
      let anyDown = false;
      blds.forEach((b, i) => {
        const s = h.buildings[i], unc = s.critDemand - s.critServed;
        m.crit_device_hours_down += s.devicesDown;
        anyDown = anyDown || s.devicesDown > 0;
        m.crit_kwh_unserved += unc; m.crit_kwh_demand += s.critDemand;
        m.person_hours_danger += b.residents * (s.tin > DANGER_C ? 1 : 0);
        m.person_degree_hours += b.residents * Math.max(0, s.tin - CAUTION_C);
        m.max_tin = Math.max(m.max_tin, s.tin);
        m.ens_kwh += unc + s.essUnserved + s.discUnserved + s.acUnserved;
        m.hw_ens += 10 * unc + 3 * s.acUnserved * (s.tin > CAUTION_C ? 1 : 0) + s.essUnserved + 0.1 * s.discUnserved;
      });
      m.hours_any_device_down += anyDown ? 1 : 0;
    }
    m.crit_served_pct = m.crit_kwh_demand ? 100 * (1 - m.crit_kwh_unserved / m.crit_kwh_demand) : 100;
    return m;
  }

  /** Full scenario: normal operation up to the outage (optionally with a 24 h warning), then the island. */
  function scenario(inp, opts) {
    const a = Object.assign(defaultAssets(), opts.assets || {});
    const blds = community();
    const start = 24 * opts.day + (opts.hour == null ? 14 : opts.hour);
    let soc0, tin0;
    const states = runNormal(inp, a, blds, 0, start + 1);
    if (opts.precharge) {
      const [s, ti] = states[start - 24];
      const st = runNormal(inp, a, blds, start - 24, start, s, ti, start - 24);
      [soc0, tin0] = st[start];
    } else {
      [soc0, tin0] = states[start];
    }
    const trace = runOutage(inp, a, blds, start, opts.duration, opts.controller, soc0, tin0, opts);
    return { trace, metrics: metrics(trace, blds), blds, soc0 };
  }

  const api = { community, defaultAssets, runNormal, runOutage, metrics, scenario, CAUTION_C, DANGER_C, SETPOINT_C };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.CareGrid = api;
})(typeof self !== "undefined" ? self : this);
