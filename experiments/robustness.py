"""Targeted PV forecast sensitivity test for Person A."""

import pathlib
import sys
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from experiments.run_pilot import INP, run_one

RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

rows = []

# Same outage conditions for every controller
job_base = (3, 14, 48, False, 150.0, 1.0, 48)

# Test shield controllers under three PV forecast assumptions
for factor in [0.4, 0.7, 1.0]:
    INP["pv_forecast_factor"] = factor

    for controller in ["shield", "mpc_shield"]:
        job = (controller, *job_base)
        result = run_one(job)
        result["pv_forecast_factor"] = factor
        rows.append(result)

# Soft controller baseline (not affected by shield forecast factor)
INP["pv_forecast_factor"] = 0.7
result = run_one(("soft", *job_base))
result["pv_forecast_factor"] = None
rows.append(result)

# Save results separately
df = pd.DataFrame(rows)
output = RESULTS / "robustness_pv_forecast.csv"
df.to_csv(output, index=False)

print("\nPV FORECAST ROBUSTNESS RESULTS")
print(df[[
    "controller",
    "pv_forecast_factor",
    "crit_device_hours_down",
    "crit_kwh_unserved",
    "hw_ens",
    "max_tin"
]].to_string(index=False))

print(f"\nSaved to: {output}")