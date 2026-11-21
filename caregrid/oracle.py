"""Linear-programming planners over the island.

* run_oracle: perfect foresight of the TRUE outage duration and the weather. Lexicographic
  objective via big weights. Device on/off is relaxed to [0, 1], so this is an upper bound
  on what any non-anticipative controller can reach.
* mpc_decision: receding-horizon MPC used as the strong "priority as a weight" baseline.
  It re-plans every hour to the utility's point estimate of restoration (minimum 12 h),
  with perfect weather/PV forecasts inside that horizon, and applies only the first hour.

Both may pre-cool down to 24 C, which the greedy controllers cannot.
"""
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

from .health_twin import vulnerability
from .sim import CAUTION_C, DANGER_C, W_DISCRETIONARY, W_ESSENTIAL, ac_needed, base_split, cop, pv_kw

PRECOOL_MIN_C = 24.0


def solve_lp(inp, assets, blds, start, T, soc0, tin0, w_crit, w_heat):
    """Returns (solution vector, index map, active-device map)."""
    B, cap = len(blds), assets.batt_kwh
    idx, bounds, dev = {}, [], {}

    def var(key, lo, hi):
        idx[key] = len(bounds)
        bounds.append((lo, hi))

    for t in range(T):
        tt = start + t
        hr, temp = inp["hour"][tt], inp["temp"][tt]
        for b, bl in enumerate(blds):
            ess, disc = base_split(bl, inp["base_kw"], hr)
            dev[t, b] = [d.kw for d in bl.devices if d.active(hr)]
            for j, _ in enumerate(dev[t, b]):
                var(("x", t, b, j), 0, 1)
            var(("e", t, b), 0, ess)
            var(("z", t, b), 0, disc)
            var(("a", t, b), 0, bl.ac_max_kw_th / cop(temp))
        var(("ch", t), 0, assets.batt_kw)
        var(("dis", t), 0, assets.batt_kw)
        var(("cur", t), 0, None)
        var(("E", t + 1), assets.soc_min * cap, cap)
        for b in range(B):
            var(("T", t + 1, b), PRECOOL_MIN_C, None)
            var(("u", t + 1, b), 0, None)

    n = len(bounds)
    c = np.zeros(n)
    eq_r, eq_c, eq_v, b_eq = [], [], [], []
    ub_r, ub_c, ub_v, b_ub = [], [], [], []

    def eq(coeffs, rhs):
        i = len(b_eq)
        for j, v in coeffs:
            eq_r.append(i); eq_c.append(j); eq_v.append(v)
        b_eq.append(rhs)

    def ub(coeffs, rhs):
        i = len(b_ub)
        for j, v in coeffs:
            ub_r.append(i); ub_c.append(j); ub_v.append(v)
        b_ub.append(rhs)

    for t in range(T):
        tt = start + t
        temp, ghi = inp["temp"][tt], inp["ghi"][tt]
        pv = pv_kw(assets, inp["poa"][tt], temp)
        bal = [(idx["ch", t], 1.0), (idx["cur", t], 1.0), (idx["dis", t], -1.0)]
        for b, bl in enumerate(blds):
            for j, kw in enumerate(dev[t, b]):
                bal.append((idx["x", t, b, j], kw))
                c[idx["x", t, b, j]] -= w_crit * kw
            bal += [(idx["e", t, b], 1.0), (idx["z", t, b], 1.0), (idx["a", t, b], 1.0)]
            c[idx["e", t, b]] -= W_ESSENTIAL
            c[idx["z", t, b]] -= W_DISCRETIONARY
        eq(bal, pv)
        soc_terms = [(idx["E", t + 1], 1.0), (idx["ch", t], -assets.eta), (idx["dis", t], 1.0 / assets.eta)]
        if t > 0:
            soc_terms.append((idx["E", t], -1.0))
        eq(soc_terms, soc0 * cap if t == 0 else 0.0)
        for b, bl in enumerate(blds):
            k = 1.0 - 1.0 / (bl.R * bl.C)
            const = (temp / bl.R + bl.solar_aperture * ghi / 1000.0 + bl.internal_kw) / bl.C
            terms = [(idx["T", t + 1, b], 1.0), (idx["a", t, b], cop(temp) / bl.C)]
            if t == 0:
                eq(terms, k * tin0[b] + const)
            else:
                eq(terms + [(idx["T", t, b], -k)], const)
            ub([(idx["T", t + 1, b], 1.0), (idx["u", t + 1, b], -1.0)], CAUTION_C)
            c[idx["u", t + 1, b]] += w_heat * bl.residents
        c[idx["cur", t]] += 1e-4

    A_eq = coo_matrix((eq_v, (eq_r, eq_c)), shape=(len(b_eq), n)).tocsr()
    A_ub = coo_matrix((ub_v, (ub_r, ub_c)), shape=(len(b_ub), n)).tocsr()
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    if res.status != 0:
        raise RuntimeError(res.message)
    return res.x, idx, dev



def run_oracle(inp, assets, blds, start, duration, soc0, tin0):
    x, idx, dev = solve_lp(
        inp, assets, blds, start, duration, soc0, tin0,
        w_crit=1000.0, w_heat=1.0
    )

    m = {
        "crit_device_hours_down": 0,
        "crit_kwh_unserved": 0.0,
        "crit_kwh_demand": 0.0,
        "person_hours_danger": 0.0,
        "person_degree_hours": 0.0,
        "ens_kwh": 0.0,
        "hw_ens": 0.0,
        "max_tin": 0.0,
        "pv_curtailed_kwh": 0.0,
        "hours_any_device_down": 0,
        "ess_kwh_unserved": 0.0,
        "vuln_degree_hours": 0.0,
    }

    for t in range(duration):
        tt = start + t
        hr = inp["hour"][tt]
        temp = inp["temp"][tt]
        ghi = inp["ghi"][tt]
        any_down = False

        m["pv_curtailed_kwh"] += max(0.0, float(x[idx["cur", t]]))

        for b, bl in enumerate(blds):
            tin = float(tin0[b] if t == 0 else x[idx["T", t, b]])

            ess_demand, disc_demand = base_split(
                bl, inp["base_kw"], hr
            )
            ess_served = float(x[idx["e", t, b]])
            disc_served = float(x[idx["z", t, b]])
            ac_demand = ac_needed(bl, tin, temp, ghi)
            ac_served = float(x[idx["a", t, b]])

            crit_unserved = 0.0
            for j, kw in enumerate(dev[t, b]):
                fraction = float(x[idx["x", t, b, j]])
                crit_unserved += kw * (1.0 - fraction)
                m["crit_kwh_demand"] += kw
                down = fraction < 0.999
                m["crit_device_hours_down"] += int(down)
                any_down = any_down or down

            ess_unserved = max(0.0, ess_demand - ess_served)
            disc_unserved = max(0.0, disc_demand - disc_served)
            ac_unserved = max(0.0, ac_demand - ac_served)

            m["crit_kwh_unserved"] += crit_unserved
            m["ess_kwh_unserved"] += ess_unserved
            m["ens_kwh"] += (
                crit_unserved + ess_unserved
                + disc_unserved + ac_unserved
            )
            m["hw_ens"] += (
                10.0 * crit_unserved
                + 3.0 * ac_unserved * (tin > CAUTION_C)
                + ess_unserved
                + 0.1 * disc_unserved
            )

            m["person_hours_danger"] += bl.residents * (tin > DANGER_C)
            m["person_degree_hours"] += (
                bl.residents * max(0.0, tin - CAUTION_C)
            )
            m["vuln_degree_hours"] += vulnerability(bl.name) * max(0.0, tin - CAUTION_C)
            m["max_tin"] = max(m["max_tin"], tin)

        m["hours_any_device_down"] += int(any_down)

    demand = m["crit_kwh_demand"]
    m["crit_served_pct"] = (
        100.0 * (1.0 - m["crit_kwh_unserved"] / demand)
        if demand else 100.0
    )

    return {k: float(v) for k, v in m.items()}


def mpc_decision(inp, assets, blds, t, soc, tin, forecast_end, w_crit, w_heat):
    """First-hour decision of a receding-horizon plan, in the controller output format."""
    T = max(12, forecast_end - t)   # same 12 h minimum look-ahead as the shield
    x, idx, dev = solve_lp(inp, assets, blds, t, T, soc, tin, w_crit, w_heat)
    return [{"devices": [bool(x[idx["x", 0, b, j]] >= 0.999) for j in range(len(dev[0, b]))],
             "ess": float(x[idx["e", 0, b]]), "ac": float(x[idx["a", 0, b]]),
             "disc": float(x[idx["z", 0, b]])} for b in range(len(blds))]
