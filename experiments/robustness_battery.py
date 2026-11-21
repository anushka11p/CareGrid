"""Battery capacity sensitivity test for Person A."""

import pathlib
import sys
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from experiments.run_pilot import run_one

RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

rows = []

for capacity in [100.0, 125.0, 150.0]:
    for controller in ["soft", "shield", "mpc_shield"]:
        job = (controller, 3, 14, 48, False, capacity, 1.0, 48)
        result = run_one(job)
        result["tested_capacity_kwh"] = capacity
        rows.append(result)

df = pd.DataFrame(rows)

output = RESULTS / "robustness_battery.csv"
df.to_csv(output, index=False)

print("\nBATTERY CAPACITY ROBUSTNESS RESULTS")
print(df[[
    "controller",
    "tested_capacity_kwh",
    "crit_device_hours_down",
    "crit_kwh_unserved",
    "hw_ens",
    "max_tin"
]].to_string(index=False))

print(f"\nSaved to: {output}")