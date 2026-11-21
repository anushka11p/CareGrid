"""Sensor temperature bias robustness test for Person A."""

import pathlib
import sys
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from experiments.run_pilot import INP, BLDS, initial_state
from caregrid.sim import Assets, run_outage, metrics

RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

rows = []

start = 24 * 3 + 14
duration = 48

# Test under-reading, accurate reading, and over-reading
for bias in [-2.0, 0.0, 2.0]:

    for controller in ["soft", "shield", "mpc_shield"]:

        assets = Assets(batt_kwh=150.0, batt_kw=60.0)

        (soc0, tin0), extra_grid = initial_state(
            assets, start, False
        )

        trace = run_outage(
            INP,
            assets,
            BLDS,
            start,
            duration,
            controller,
            soc0,
            tin0,
            forecast_hours=24,
            p90_hours=48,
            w_heat=1.0,
            sensor_bias_c=bias
        )

        result = metrics(trace, BLDS)
        result["controller"] = controller
        result["sensor_bias_c"] = bias
        rows.append(result)

df = pd.DataFrame(rows)

output = RESULTS / "robustness_sensor.csv"
df.to_csv(output, index=False)

print("\nSENSOR BIAS ROBUSTNESS RESULTS")
print(df[[
    "controller",
    "sensor_bias_c",
    "crit_device_hours_down",
    "crit_kwh_unserved",
    "hw_ens",
    "max_tin",
    "person_hours_danger"
]].to_string(index=False))

print(f"\nSaved to: {output}")