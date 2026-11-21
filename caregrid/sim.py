"""CareGrid pilot: a community microgrid serving elderly households through a heatwave outage.

One hourly time step. Physics per building is a 1R1C grey-box thermal model with an
air conditioner whose COP falls with outdoor temperature. The community shares one PV
array and one battery. During an outage the microgrid islands and a controller decides,
every hour, which loads get the scarce energy.

Every controller here is deterministic and is mirrored line-for-line in demo/engine.js;
tests/test_parity.py checks the two produce identical results.
"""
from dataclasses import dataclass, field
import json
import pathlib

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "processed" / "phoenix_july2023.json"

# ---------------------------------------------------------------- parameters
SETPOINT_C = 26.0          # thermostat setpoint when power is available
CAUTION_C = 26.7           # NWS heat-index "caution" lower bound (80 F)
DANGER_C = 32.2            # NWS "extreme caution" lower bound (90 F)
ESSENTIAL_KW = 0.35        # per home-equivalent: food fridge, lights, phone, fans
GRID_CO2_KG_PER_KWH = 0.352  # ASSUMPTION: EPA eGRID2022 AZNM average output rate (~776 lb/MWh); verify

# Values a controller places on one kWh of each load type (used by soft and shield).
W_CRITICAL = 10.0
W_ESSENTIAL = 2.0
W_DISCRETIONARY = 0.1


@dataclass
class Device:
    name: str
    kw: float
    hours: tuple = ()      # empty = runs 24/7
    priority: int = 3      # 1 = highest, 3 = lowest

    def active(self, hour):
        return not self.hours or hour in self.hours


NIGHT = tuple(list(range(22, 24)) + list(range(0, 6)))


@dataclass
class Building:
    name: str
    residents: int
    scale: float = 1.0      # thermal and base-load size in home-equivalents
    devices: list = field(default_factory=list)

    # 1R1C parameters, calibrated in experiments/calibrate.py against ResStock July cooling energy
    @property
    def R(self):            # degC per kW
        return 1.75 / self.scale

    @property
    def C(self):            # kWh per degC
        return 6.0 * self.scale

    @property
    def ac_max_kw_th(self):
        return 14.0 * self.scale    # ~4-ton unit per home-equivalent (typical Phoenix sizing)

    @property
    def solar_aperture(self):   # kW of heat gain per 1 kW/m2 horizontal irradiance
        return 1.2 * self.scale

    @property
    def internal_kw(self):
        return 0.3 * self.scale + 0.1 * self.residents


def community():
    """Eight elderly households and one small care facility.

    Simulation priority assumption:
    1 = life-sustaining support
    2 = essential medical storage
    3 = other health-related equipment
    """
    O2 = lambda n="oxygen concentrator": Device(n, 0.35, priority=1)
    return [
        Building("H1", 1, devices=[O2()]),
        Building("H2", 2, devices=[
            Device("CPAP", 0.06, NIGHT, priority=3),
            Device("insulin fridge", 0.12, priority=2),
        ]),
        Building("H3", 1, devices=[O2()]),
        Building("H4", 1),
        Building("H5", 2, devices=[
            Device("power wheelchair charger", 0.30, (22, 23, 0, 1), priority=3),
        ]),
        Building("H6", 1, devices=[
            Device("CPAP", 0.06, NIGHT, priority=3),
            Device("insulin fridge", 0.12, priority=2),
        ]),
        Building("H7", 1, devices=[O2()]),
        Building("H8", 2),
        Building("Care facility", 6, scale=4.0, devices=[
            O2("oxygen concentrator A"),
            O2("oxygen concentrator B"),
            Device("ventilator", 0.15, priority=1),
            Device("medication fridge", 0.15, priority=2),
        ]),
    ]


@dataclass
class Assets:
    pv_kwp: float = 60.0
    batt_kwh: float = 150.0
    batt_kw: float = 60.0
    soc_min: float = 0.10
    reserve_grid: float = 0.30   # backup reserve kept while grid-connected
    eta: float = 0.95            # one-way charge / discharge efficiency


# ---------------------------------------------------------------- inputs
def load_inputs(path=DATA):
    d = json.loads(pathlib.Path(path).read_text())
    w = d["weather"]
    hours = [int(t[11:13]) for t in w["time"]]
    return {"time": w["time"], "hour": hours, "temp": w["temp_c"], "ghi": w["ghi_wm2"],
            "poa": w["poa_wm2"], "base_kw": d["resstock"]["base_kw_by_hour"]}


def pv_kw(assets, poa, temp):
    t_cell = temp + (45.0 - 20.0) / 800.0 * poa           # NOCT model
    return max(0.0, assets.pv_kwp * poa / 1000.0 * 0.86 * (1 - 0.0035 * (t_cell - 25.0)))


def cop(temp):
    return min(4.0, max(2.0, 4.0 - 0.06 * (temp - 30.0)))


def heat_gain(b, t_in, temp, ghi):
    """Net heat flowing into the building over one hour with the AC off, in kWh."""
    return (temp - t_in) / b.R + b.solar_aperture * ghi / 1000.0 + b.internal_kw


def next_temp(b, t_in, temp, ghi, ac_kw_el):
    return t_in + (heat_gain(b, t_in, temp, ghi) - cop(temp) * ac_kw_el) / b.C


def ac_needed(b, t_in, temp, ghi):
    """Electric kW to land exactly on the setpoint at the end of the hour."""
    q = (t_in - SETPOINT_C) * b.C + heat_gain(b, t_in, temp, ghi)
    return min(b.ac_max_kw_th, max(0.0, q)) / cop(temp)


def base_split(b, base_kw, hour):
    total = base_kw[hour] * b.scale
    ess = min(total, ESSENTIAL_KW * b.scale)
    return ess, total - ess


def crit_demand(blds, hour):
    return sum(d.kw for b in blds for d in b.devices if d.active(hour))


# ---------------------------------------------------------------- grid-connected operation
def run_normal(inp, assets, blds, t0=0, t1=None, soc0=0.5, tin0=None, precharge_from=None):
    """Grid-connected operation. Returns per-hour state (soc and indoor temps at the START
    of each hour) plus energy flows. If precharge_from is set, from that hour on the
    battery charges to full from PV then grid and stops discharging (outage alert)."""
    t1 = len(inp["temp"]) if t1 is None else t1
    soc = soc0
    tin = list(tin0) if tin0 else [SETPOINT_C] * len(blds)
    states, flows = {}, []
    cap = assets.batt_kwh
    for t in range(t0, t1):
        states[t] = (soc, list(tin))
        hr, temp, ghi = inp["hour"][t], inp["temp"][t], inp["ghi"][t]
        pv = pv_kw(assets, inp["poa"][t], temp)
        load = crit_demand(blds, hr)
        for i, b in enumerate(blds):
            ac = ac_needed(b, tin[i], temp, ghi)
            load += ac + inp["base_kw"][hr] * b.scale
            tin[i] = next_temp(b, tin[i], temp, ghi, ac)
        net = load - pv
        precharging = precharge_from is not None and t >= precharge_from
        charge = discharge = 0.0
        if net < 0:
            charge = min(-net, assets.batt_kw, (1 - soc) * cap / assets.eta)
        elif not precharging:
            discharge = min(net, assets.batt_kw, max(0.0, soc - assets.reserve_grid) * cap * assets.eta)
        if precharging:
            charge = min(assets.batt_kw, (1 - soc) * cap / assets.eta)
        soc += (charge * assets.eta - discharge / assets.eta) / cap
        grid = load + charge - pv - discharge
        flows.append({"t": t, "load": load, "pv": pv, "grid_import": max(0.0, grid),
                      "export": max(0.0, -grid), "charge": charge, "discharge": discharge})
    states[t1] = (soc, list(tin))
    return states, flows


# ---------------------------------------------------------------- outage controllers
def _demands(inp, blds, t, tin):
    hr, temp, ghi = inp["hour"][t], inp["temp"][t], inp["ghi"][t]
    rows = []
    for i, b in enumerate(blds):
        ess, disc = base_split(b, inp["base_kw"], hr)
        t_noac = next_temp(b, tin[i], temp, ghi, 0.0)
        rows.append({
            "devices": [d.kw for d in b.devices if d.active(hr)],
            "device_priorities": [d.priority for d in b.devices if d.active(hr)],
            "ess": ess, "disc": disc, "ac": ac_needed(b, tin[i], temp, ghi),
            "safe_ac": min(
                max(0.0, (heat_gain(b, tin[i], temp, ghi) - b.C * (CAUTION_C - tin[i])) / cop(temp)),
                b.ac_max_kw_th / cop(temp),
            ),
            "risk": max(0.0, t_noac - CAUTION_C) / (DANGER_C - CAUTION_C) * b.residents,
        })
    return rows


def _greedy(items, budget):
    """items: list of (value_per_kwh, key, kw, divisible). Fills highest value first.
    Atomic items (medical devices) are skipped if they do not fit whole."""
    alloc = {}
    for value, key, kw, divisible in sorted(items, key=lambda x: (-x[0], x[1])):
        if kw <= budget + 1e-9:
            alloc[key] = kw
            budget -= kw
        elif divisible and budget > 1e-9:
            alloc[key] = budget
            budget = 0.0
        else:
            alloc[key] = 0.0
    return alloc, budget


def _items(rows, w_heat, include_crit=True):
    items = []
    for i, r in enumerate(rows):
        if include_crit:
            for j, kw in enumerate(r["devices"]):
                items.append((W_CRITICAL, f"{i:02d}d{j}", kw, False))
        items.append((W_ESSENTIAL, f"{i:02d}e", r["ess"], True))
        items.append((w_heat * r["risk"], f"{i:02d}a", r["ac"], True))
        items.append((W_DISCRETIONARY, f"{i:02d}x", r["disc"], True))
    return items


def _unpack(rows, alloc):
    out = []
    for i, r in enumerate(rows):
        out.append({
            "devices": [alloc.get(f"{i:02d}d{j}", 0.0) >= kw - 1e-9 for j, kw in enumerate(r["devices"])],
            "ess": alloc.get(f"{i:02d}e", 0.0), "ac": alloc.get(f"{i:02d}a", 0.0),
            "disc": alloc.get(f"{i:02d}x", 0.0)})
    return out


def ctrl_equal(rows, ctx):
    """Status quo: every load is curtailed by the same fraction; medical devices trip
    whenever they get less than full power. Battery is spent greedily."""
    demand = sum(sum(r["devices"]) + r["ess"] + r["ac"] + r["disc"] for r in rows)
    f = 1.0 if demand <= 1e-9 else min(1.0, ctx["supply"] / demand)
    return [{"devices": [f >= 1 - 1e-9] * len(r["devices"]), "ess": f * r["ess"],
             "ac": f * r["ac"], "disc": f * r["disc"]} for r in rows]


def ctrl_rule(rows, ctx):
    """Industry heuristic: critical, then essential loads; AC and discretionary only when
    battery SoC > 40%, otherwise only from instantaneous PV."""
    crit_items = sorted(((kw, f"{i:02d}d{j}") for i, r in enumerate(rows)
                         for j, kw in enumerate(r["devices"])))
    budget, alloc = ctx["supply"], {}
    for kw, key in crit_items:
        alloc[key] = kw if kw <= budget + 1e-9 else 0.0
        budget -= alloc[key]
    for i, r in enumerate(rows):
        e = min(r["ess"], budget)
        alloc[f"{i:02d}e"] = e
        budget -= e
    used = ctx["supply"] - budget
    flex = budget if ctx["soc"] > 0.40 else max(0.0, min(budget, ctx["pv"] - used))
    want = sum(r["ac"] + r["disc"] for r in rows)
    f = 1.0 if want <= 1e-9 else min(1.0, flex / want)
    for i, r in enumerate(rows):
        alloc[f"{i:02d}a"] = f * r["ac"]
        alloc[f"{i:02d}x"] = f * r["disc"]
    return _unpack(rows, alloc)


def _paced_budget(ctx, batt_kwh_avail):
    remaining = max(1.0, ctx["forecast_end"] - ctx["t"])
    return min(ctx["supply"], ctx["pv"] + min(ctx["batt_kw_avail"], batt_kwh_avail / remaining))


def ctrl_soft(rows, ctx):
    """Priority as a REWARD WEIGHT. Critical loads compete with cooling on value per kWh;
    battery is paced to last until the utility's point estimate of restoration. Steelman:
    the budget is never below the critical demand when energy exists."""
    crit = sum(sum(r["devices"]) for r in rows)
    budget = max(_paced_budget(ctx, ctx["batt_kwh_avail"]), min(ctx["supply"], crit))
    alloc, _ = _greedy(_items(rows, ctx["w_heat"]), budget)
    return _unpack(rows, alloc)


def _shield_budget(rows, ctx):
    """The runtime shield. (1) Critical devices are served first whenever any energy
    exists. (2) A battery reserve sized to carry every critical device through the
    worst-case (P90) restoration time, net of a conservative PV forecast, is locked;
    below it, surplus PV refills the battery before anything else runs. Returns the
    critical allocation and the kW budget left for non-critical loads this hour."""
    crit_items = sorted(
        (priority, i, j, kw, f"{i:02d}d{j}")
        for i, r in enumerate(rows)
        for j, kw in enumerate(r["devices"])
        for priority in [r["device_priorities"][j]]
    )
    budget, alloc = ctx["supply"], {}
    for priority, i, j, kw, key in crit_items:
        alloc[key] = kw if kw <= budget + 1e-9 else 0.0
        budget -= alloc[key]
    crit_used = ctx["supply"] - budget
    from_batt_for_crit = max(0.0, crit_used - ctx["pv"])
    free_kwh = max(0.0, ctx["batt_kwh_avail"] - from_batt_for_crit - ctx["reserve_kwh"])
    pv_left = max(0.0, ctx["pv"] - crit_used)
    deficit_kwh = max(0.0, ctx["reserve_kwh"] - (ctx["batt_kwh_avail"] - from_batt_for_crit))
    # Below the reserve, surplus PV refills the battery before anything non-critical runs.
    pv_left = max(0.0, pv_left - min(deficit_kwh / ctx["eta"] ** 2, ctx["batt_kw"]))
    batt_kw_left = max(0.0, ctx["batt_kw_avail"] - from_batt_for_crit)
    remaining = max(1.0, ctx["forecast_end"] - ctx["t"])
    return alloc, min(budget, pv_left + min(batt_kw_left, free_kwh / remaining))



def _thermal_shield_items(rows, ctx, nc_budget):
    """Allocate thermal safety cooling before other flexible loads."""
    alloc, remaining = _shield_budget(rows, ctx)
    remaining = min(remaining, nc_budget)

    # Prioritize cooling needed to keep next-hour indoor temperature safe.
    for i, r in enumerate(rows):
        key = f"{i:02d}a"
        cooling = min(r["safe_ac"], remaining)
        alloc[key] = cooling
        remaining -= cooling

    # Allocate leftover power to essential and discretionary loads.
    other_items = []
    for i, r in enumerate(rows):
        other_items.append(
            (W_ESSENTIAL, f"{i:02d}e", r["ess"], True)
        )
        other_items.append(
            (W_DISCRETIONARY, f"{i:02d}x", r["disc"], True)
        )

    more, _ = _greedy(other_items, remaining)
    alloc.update(more)
    return alloc

def ctrl_shield(rows, ctx):
    """Prioritize medical devices, then thermal safety cooling."""
    _, nc_budget = _shield_budget(rows, ctx)
    alloc = _thermal_shield_items(rows, ctx, nc_budget)
    return _unpack(rows, alloc)




def apply_shield(rows, ctx, proposal):
    """Protect critical devices, then prioritize thermal safety cooling."""
    _, nc_budget = _shield_budget(rows, ctx)
    alloc = _thermal_shield_items(rows, ctx, nc_budget)

    # Keep the thermal shield's cooling allocation.
    cooling_used = sum(alloc.get(f"{i:02d}a", 0.0)
                       for i in range(len(rows)))
    remaining = max(0.0, nc_budget - cooling_used)

    # Allocate remaining power to the MPC's proposed essential loads first.
    essential_items = [
        (W_ESSENTIAL, f"{i:02d}e", p["ess"], True)
        for i, p in enumerate(proposal)
    ]
    essential_alloc, remaining = _greedy(essential_items, remaining)

    # Then allocate power to proposed discretionary loads.
    discretionary_items = [
        (W_DISCRETIONARY, f"{i:02d}x", p["disc"], True)
        for i, p in enumerate(proposal)
    ]
    discretionary_alloc, _ = _greedy(discretionary_items, remaining)

    alloc.update(essential_alloc)
    alloc.update(discretionary_alloc)
    return _unpack(rows, alloc)



CONTROLLERS = {"equal": ctrl_equal, "rule": ctrl_rule, "soft": ctrl_soft, "shield": ctrl_shield}
# Receding-horizon LP planners (Python only; see oracle.py).
# name -> (critical weight, shielded?, plan to the P90 restoration time instead of the point estimate?)
MPC_CONTROLLERS = {
    "mpc": (W_CRITICAL, False, False),
    "mpc_hi": (1000.0, False, False),
    "mpc_p90": (1000.0, False, True),
    "mpc_shield": (W_CRITICAL, True, False),
    "mpc_p90_shield": (1000.0, True, True),
}
SHIELDED = {"shield", "mpc_shield", "mpc_p90_shield"}


def shield_reserve(inp, assets, blds, t, p90_end, pv_hist):
    """kWh (at the battery terminals) needed to carry critical devices from t+1 to the
    worst-case end, minus 70% of yesterday's PV at the same hours (persistence forecast)."""
    horizon = max(12, p90_end - t)
    need = 0.0
    for k in range(1, horizon + 1):
        hr = inp["hour"][(t + k) % len(inp["hour"])]
        pv_f = float(inp.get("pv_forecast_factor", 0.7)) * pv_hist[(t + k - 24) % len(pv_hist)]
        need += max(0.0, crit_demand(blds, hr) - pv_f)
    return need


# ---------------------------------------------------------------- outage simulation
def run_outage(inp, assets, blds, start, duration, controller, soc0, tin0,
               forecast_hours=24, p90_hours=48, w_heat=1.0,
               sensor_bias_c=0.0):
    ctrl = CONTROLLERS.get(controller)
    cap = assets.batt_kwh
    soc, tin = soc0, list(tin0)
    pv_hist = [pv_kw(assets, p, tt) for p, tt in zip(inp["poa"], inp["temp"])]
    trace = []
    for t in range(start, start + duration):
        hr, temp, ghi = inp["hour"][t], inp["temp"][t], inp["ghi"][t]
        pv = pv_hist[t]
        batt_kwh_avail = max(0.0, soc - assets.soc_min) * cap * assets.eta
        batt_kw_avail = min(assets.batt_kw, batt_kwh_avail)
        ctx = {"t": t, "pv": pv, "soc": soc, "batt_kwh_avail": batt_kwh_avail,
               "batt_kw_avail": batt_kw_avail, "supply": pv + batt_kw_avail,
               "forecast_end": start + forecast_hours, "w_heat": w_heat, "reserve_kwh": 0.0,
               "eta": assets.eta, "batt_kw": assets.batt_kw}
        if controller in SHIELDED:
            ctx["reserve_kwh"] = shield_reserve(inp, assets, blds, t, start + p90_hours, pv_hist)
        sensed_tin = [x + sensor_bias_c for x in tin]
        rows = _demands(inp, blds, t, sensed_tin)
        if ctrl:
            dec = ctrl(rows, ctx)
        else:
            from .oracle import mpc_decision
            w_crit, shielded, robust = MPC_CONTROLLERS[controller]
            plan_end = start + p90_hours if robust else ctx["forecast_end"]
            dec = mpc_decision(inp, assets, blds, t, soc, sensed_tin, plan_end, w_crit, w_heat)
            if shielded:
                dec = apply_shield(rows, ctx, dec)

        used = 0.0
        hour = {"t": t, "time": inp["time"][t], "temp_out": temp, "pv": pv, "buildings": []}
        for i, (b, r, d) in enumerate(zip(blds, rows, dec)):
            served_kw = sum(kw for kw, ok in zip(r["devices"], d["devices"]) if ok)
            used += served_kw + d["ess"] + d["ac"] + d["disc"]
            hour["buildings"].append({
                "tin": tin[i], "crit_demand": sum(r["devices"]), "crit_served": served_kw,
                "devices_down": sum(1 for ok in d["devices"] if not ok),
                "ess_unserved": r["ess"] - d["ess"], "disc_unserved": r["disc"] - d["disc"],
                "ac_unserved": max(0.0, r["ac"] - d["ac"])})
            tin[i] = next_temp(b, tin[i], temp, ghi, d["ac"])
        net = used - pv
        if net > 0:
            soc -= net / assets.eta / cap
            curtailed = 0.0
        else:
            charge = min(-net, assets.batt_kw, (1 - soc) * cap / assets.eta)
            soc += charge * assets.eta / cap
            curtailed = -net - charge
        soc = max(assets.soc_min - 1e-9, soc)
        hour.update({"soc": soc, "pv_curtailed": curtailed, "reserve_kwh": ctx["reserve_kwh"]})
        trace.append(hour)
    return trace


def metrics(trace, blds):
    m = {"crit_device_hours_down": 0, "crit_kwh_unserved": 0.0, "crit_kwh_demand": 0.0,
         "person_hours_danger": 0.0, "person_degree_hours": 0.0, "ens_kwh": 0.0,
         "hw_ens": 0.0, "max_tin": 0.0, "pv_curtailed_kwh": 0.0, "hours_any_device_down": 0,
         "ess_kwh_unserved": 0.0}
    for h in trace:
        m["pv_curtailed_kwh"] += h["pv_curtailed"]
        any_down = False
        for b, s in zip(blds, h["buildings"]):
            unc = s["crit_demand"] - s["crit_served"]
            m["crit_device_hours_down"] += s["devices_down"]
            any_down |= s["devices_down"] > 0
            m["crit_kwh_unserved"] += unc
            m["crit_kwh_demand"] += s["crit_demand"]
            m["person_hours_danger"] += b.residents * (s["tin"] > DANGER_C)
            m["person_degree_hours"] += b.residents * max(0.0, s["tin"] - CAUTION_C)
            m["max_tin"] = max(m["max_tin"], s["tin"])
            m["ens_kwh"] += unc + s["ess_unserved"] + s["disc_unserved"] + s["ac_unserved"]
            m["ess_kwh_unserved"] += s["ess_unserved"]
            # Health-weighted ENS: critical x10, cooling withheld while indoors is above
            # the caution line x3, essential x1, discretionary x0.1.
            m["hw_ens"] += (10 * unc + 3 * s["ac_unserved"] * (s["tin"] > CAUTION_C)
                            + s["ess_unserved"] + 0.1 * s["disc_unserved"])
        m["hours_any_device_down"] += any_down
    d = m["crit_kwh_demand"]
    m["crit_served_pct"] = 100.0 * (1 - m["crit_kwh_unserved"] / d) if d else 100.0
    return m
