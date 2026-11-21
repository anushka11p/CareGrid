import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from experiments.run_pilot import INP, BLDS, start_index, initial_state
from caregrid.sim import Assets, run_outage, _demands

assets = Assets(batt_kwh=150.0, batt_kw=60.0)
start = start_index(3, 14)
(soc, tin), _ = initial_state(assets, start, False)

trace = run_outage(
    INP, assets, BLDS, start, 12,
    "shield", soc, tin,
    forecast_hours=24, p90_hours=48, w_heat=1.0
)

print("TIME | INDOOR MAX | AC DEMAND | SAFE COOLING | AC UNSERVED")

for hour in trace:
    t = hour["t"]
    indoor = [x["tin"] for x in hour["buildings"]]
    rows = _demands(INP, BLDS, t, indoor)

    ac_demand = sum(r["ac"] for r in rows)
    safe_cooling = sum(r["safe_ac"] for r in rows)
    ac_unserved = sum(x["ac_unserved"] for x in hour["buildings"])

    print(
        f'{hour["time"]} | {max(indoor):.2f} | '
        f'{ac_demand:.2f} | {safe_cooling:.2f} | {ac_unserved:.2f}'
    )