"""Run every pilot experiment and write results/*.csv.

Scenario grid (main experiment):
  * 28 outage start days (1-28 July 2023, 14:00 local), real Phoenix weather
  * true outage durations 12 / 24 / 48 / 72 h; every controller is told the utility's
    point estimate (24 h); shielded controllers also get a P90 bound (48 h)
  * with and without a 24 h outage warning (pre-charge the battery from PV + grid)
Sweeps: heat weight, battery size, P90 bound, outage start hour.
"""
import itertools
import json
import pathlib
import sys
import time
from multiprocessing import Pool

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from caregrid.oracle import run_oracle  # noqa: E402
from caregrid.sim import (GRID_CO2_KG_PER_KWH, Assets, community, load_inputs, metrics,  # noqa: E402
                          run_normal, run_outage)

RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

INP = load_inputs()
BLDS = community()
DAYS = range(1, 29)
DURATIONS = [12, 24, 48, 72]
MAIN = ["equal", "rule", "soft", "shield", "mpc", "mpc_hi", "mpc_p90", "mpc_shield", "mpc_p90_shield", "oracle"]
_normal_cache = {}


def start_index(day, hour=14):
    return 24 * day + hour   # index 0 is 2023-06-30 00:00


def initial_state(assets, start, precharge):
    key = (assets.batt_kwh, assets.pv_kwp)
    if key not in _normal_cache:
        _normal_cache[key] = run_normal(INP, assets, BLDS)
    states, flows = _normal_cache[key]
    if not precharge:
        return states[start], 0.0
    soc, tin = states[start - 24]
    st, fl = run_normal(INP, assets, BLDS, t0=start - 24, t1=start, soc0=soc, tin0=tin,
                        precharge_from=start - 24)
    extra_grid = sum(f["grid_import"] for f in fl) - sum(f["grid_import"] for f in flows[start - 24:start])
    return st[start], extra_grid


def run_one(job):
    ctrl, day, hour, dur, precharge, batt, w_heat, p90 = job
    assets = Assets(batt_kwh=batt, batt_kw=batt * 0.4)
    start = start_index(day, hour)
    (soc0, tin0), extra_grid = initial_state(assets, start, precharge)
    if ctrl == "oracle":
        m = run_oracle(INP, assets, BLDS, start, dur, soc0, tin0)
    else:
        m = metrics(run_outage(INP, assets, BLDS, start, dur, ctrl, soc0, tin0,
                               forecast_hours=24, p90_hours=p90, w_heat=w_heat), BLDS)
    return {"controller": ctrl, "day": day, "start_hour": hour, "duration_h": dur,
            "precharge": precharge, "batt_kwh": batt, "w_heat": w_heat, "p90_h": p90,
            "soc0": soc0, "precharge_extra_grid_kwh": extra_grid, **m}


def jobs():
    out = []
    # main grid
    for ctrl, day, dur, pre in itertools.product(MAIN, DAYS, DURATIONS, [False, True]):
        out.append(("main", (ctrl, day, 14, dur, pre, 150.0, 1.0, 48)))
    # heat-weight sweep (48 h, no warning)
    for ctrl, day, w in itertools.product(["soft", "shield", "mpc", "mpc_p90_shield"], DAYS, [0.25, 0.5, 1, 2, 4, 8]):
        out.append(("w_heat", (ctrl, day, 14, 48, False, 150.0, w, 48)))
    # battery sweep (48 h, no warning)
    for ctrl, day, batt in itertools.product(["equal", "rule", "soft", "shield", "mpc", "mpc_p90", "mpc_p90_shield", "oracle"],
                                             DAYS, [75.0, 100.0, 150.0, 250.0, 400.0]):
        out.append(("battery", (ctrl, day, 14, 48, False, batt, 1.0, 48)))
    # P90 sensitivity for the shield
    for ctrl, day, dur, p90 in itertools.product(["shield", "mpc_p90_shield"], DAYS, DURATIONS, [24, 36, 48, 72, 96]):
        out.append(("p90", (ctrl, day, 14, dur, False, 150.0, 1.0, p90)))
    # start-hour sensitivity (48 h, no warning)
    for ctrl, day, hour in itertools.product(["equal", "rule", "soft", "shield", "mpc", "mpc_p90", "mpc_p90_shield", "oracle"],
                                             DAYS, [2, 8, 14, 20]):
        out.append(("start_hour", (ctrl, day, hour, 48, False, 150.0, 1.0, 48)))
    return out


def grid_month():
    """Grid-connected July 2023 for the community, normal operation."""
    assets = Assets()
    _, flows = run_normal(INP, assets, BLDS)
    jul = [f for f in flows if INP["time"][f["t"]].startswith("2023-07")]
    load = sum(f["load"] for f in jul)
    pv = sum(f["pv"] for f in jul)
    imp = sum(f["grid_import"] for f in jul)
    exp_ = sum(f["export"] for f in jul)
    return {"load_kwh": load, "pv_kwh": pv, "grid_import_kwh": imp, "export_kwh": exp_,
            "pv_self_consumption_pct": 100 * (pv - exp_) / pv, "self_sufficiency_pct": 100 * (load - imp) / load,
            "grid_co2_t": imp * GRID_CO2_KG_PER_KWH / 1000,
            "co2_avoided_by_pv_t": (pv - exp_) * GRID_CO2_KG_PER_KWH / 1000}


if __name__ == "__main__":
    t0 = time.time()
    js = jobs()
    print(f"{len(js)} simulations")
    with Pool() as pool:
        rows = pool.map(run_one, [j for _, j in js], chunksize=8)
    df = pd.DataFrame(rows)
    df.insert(0, "experiment", [e for e, _ in js])
    df.to_csv(RESULTS / "scenarios.csv", index=False)
    (RESULTS / "grid_month.json").write_text(json.dumps(grid_month(), indent=2))
    print(f"done in {time.time() - t0:.0f}s -> results/scenarios.csv")
