"""Step 7 (robustness): Person A's single-outage sensitivity tests repeated over all 28 start days.

Factors, one at a time with the others at baseline: PV forecast factor {0.4, 0.7, 1.0},
indoor-temperature sensor bias {-2, 0, +2} C, community battery {100, 125, 150} kWh.
Controllers soft (priority as weight) and shield; 48 h and 72 h outages, no warning.
Writes personC/step7/robustness.csv and robustness.md.
"""
import itertools
import pathlib
import sys
from multiprocessing import Pool

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from caregrid.sim import Assets, community, load_inputs, metrics, run_normal, run_outage  # noqa: E402

LEVELS = {"pv_forecast_factor": (0.4, 0.7, 1.0), "sensor_bias_c": (-2.0, 0.0, 2.0), "battery_kwh": (100.0, 125.0, 150.0)}
_cache = {}


def run(job):
    factor, level, ctrl, day, dur = job
    batt = level if factor == "battery_kwh" else 150.0
    if batt not in _cache:
        inp, a, blds = load_inputs(), Assets(batt_kwh=batt, batt_kw=batt * 0.4), community()
        _cache[batt] = (inp, a, blds, run_normal(inp, a, blds)[0])
    inp, a, blds, states = _cache[batt]
    inp = dict(inp, pv_forecast_factor=level if factor == "pv_forecast_factor" else 0.7)
    start = 24 * day + 14
    soc0, tin0 = states[start]
    m = metrics(run_outage(inp, a, blds, start, dur, ctrl, soc0, tin0,
                           sensor_bias_c=level if factor == "sensor_bias_c" else 0.0), blds)
    return {"factor": factor, "level": level, "controller": ctrl, "day": day, "duration_h": dur, **m}


if __name__ == "__main__":
    out = pathlib.Path(__file__).resolve().parent
    jobs = [(f, lv, c, d, du) for f, lvs in LEVELS.items()
            for lv, c, d, du in itertools.product(lvs, ("soft", "shield"), range(1, 29), (48, 72))]
    with Pool(6) as p:
        df = pd.DataFrame(p.map(run, jobs, chunksize=6))
    df.to_csv(out / "robustness.csv", index=False)
    t = df.pivot_table(index=["factor", "level"], columns=["controller", "duration_h"],
                       values=["crit_device_hours_down", "person_hours_danger"], aggfunc="mean").round(1)
    (out / "robustness.md").write_text("# Robustness over 28 start days (no warning)\n\n" + t.to_markdown() + "\n")
    print(t.to_string())
