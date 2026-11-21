"""Step 1: measure the shield before/after the reserve-refill fix.

Usage: python personC/step1/measure.py before|after
Runs soft, shield and mpc_shield on every outage start 1-28 July (14:00) for 12/24/48/72 h,
no warning, and writes personC/step1/<label>.csv."""
import itertools
import pathlib
import sys
from multiprocessing import Pool

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from caregrid.sim import Assets, community, load_inputs, metrics, run_normal, run_outage  # noqa: E402

INP, A, BLDS = load_inputs(), Assets(), community()
STATES, _ = run_normal(INP, A, BLDS)


def run(job):
    ctrl, day, dur = job
    start = 24 * day + 14
    soc0, tin0 = STATES[start]
    m = metrics(run_outage(INP, A, BLDS, start, dur, ctrl, soc0, tin0), BLDS)
    return {"controller": ctrl, "day": day, "duration_h": dur, **m}


if __name__ == "__main__":
    label = sys.argv[1]
    jobs = list(itertools.product(["soft", "shield", "mpc_shield"], range(1, 29), (12, 24, 48, 72)))
    with Pool(6) as p:
        rows = p.map(run, jobs, chunksize=4)
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "personC" / "step1" / f"{label}.csv", index=False)
    print(label)
    print(df.groupby(["controller", "duration_h"]).crit_device_hours_down.mean().unstack().round(1).to_string())
    case = df[(df.day == 19) & (df.duration_h == 48)][["controller", "crit_device_hours_down", "person_hours_danger"]]
    print("\n19 July 14:00, 48 h:\n" + case.to_string(index=False))
