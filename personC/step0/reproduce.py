"""Step 0: check that the handed-over code reproduces the handed-over results.

Re-runs a random sample of rows of results/scenarios.csv with experiments/run_pilot.run_one
and compares every metric column."""
import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.run_pilot import run_one  # noqa: E402

df = pd.read_csv(ROOT / "results" / "scenarios.csv")
sample = df[~df.controller.str.startswith("mpc") & (df.controller != "oracle")].sample(60, random_state=0)
sample = pd.concat([sample, df[df.controller.str.startswith("mpc") | (df.controller == "oracle")].sample(20, random_state=0)])
metrics = ["crit_device_hours_down", "crit_kwh_unserved", "person_hours_danger", "person_degree_hours", "max_tin"]
rows, worst = [], 0.0
for _, r in sample.iterrows():
    job = (r.controller, int(r.day), int(r.start_hour), int(r.duration_h), bool(r.precharge),
           float(r.batt_kwh), float(r.w_heat), int(r.p90_h))
    new = run_one(job)
    diff = max(abs(new[m] - r[m]) for m in metrics)
    worst = max(worst, diff)
    rows.append({**{k: r[k] for k in ["experiment", "controller", "day", "duration_h"]},
                 "stored_dev_h": r.crit_device_hours_down, "rerun_dev_h": new["crit_device_hours_down"], "max_diff": diff})
out = pd.DataFrame(rows)
out.to_csv(ROOT / "personC" / "step0" / "reproduce_sample.csv", index=False)
bad = out[out.max_diff > 1e-6]
print(f"rows checked: {len(out)}, max abs difference: {worst:.3g}, mismatches: {len(bad)}")
if len(bad):
    print(bad.groupby("controller").size().to_string())
    print(bad.head(10).to_string(index=False))
