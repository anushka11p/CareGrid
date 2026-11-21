import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from experiments.run_pilot import INP, BLDS, start_index, initial_state
from caregrid.sim import Assets, run_outage

assets = Assets(batt_kwh=150.0, batt_kw=60.0)
start = start_index(3, 14)

(soc, tin), _ = initial_state(assets, start, False)

trace = run_outage(
    INP, assets, BLDS, start, 12,
    "shield", soc, tin,
    forecast_hours=24, p90_hours=48, w_heat=1.0
)

print("TIME | PV kW | BATTERY SOC | RESERVE kWh")

for h in trace:
    print(
        h["time"], "|",
        round(h["pv"], 2), "|",
        round(h["soc"], 3), "|",
        round(h["reserve_kwh"], 2)
    )