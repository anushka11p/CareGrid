"""Check the 1R1C home model against NREL ResStock: an average Maricopa single-family
home used 51.1 kWh/day of cooling in July 2018. July 2023 was hotter, so the model
should land somewhat above that, and indoor temperature should hold at the setpoint."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from caregrid.sim import Building, SETPOINT_C, ac_needed, load_inputs, next_temp, DATA  # noqa: E402

inp = load_inputs()
b = Building("avg", 2)
tin, ac_kwh, days = SETPOINT_C, 0.0, 0
july = [i for i, t in enumerate(inp["time"]) if t.startswith("2023-07")]
for t in range(july[0] - 24, july[-1] + 1):
    ac = ac_needed(b, tin, inp["temp"][t], inp["ghi"][t])
    tin = next_temp(b, tin, inp["temp"][t], inp["ghi"][t], ac)
    if t >= july[0]:
        ac_kwh += ac
res = json.loads(DATA.read_text())["resstock"]
print(f"model July 2023 cooling: {ac_kwh / 31:.1f} kWh/day per home")
print(f"ResStock July 2018 cooling: {res['july2018_cooling_kwh_per_day']} kWh/day per home")
jul_t = [inp["temp"][t] for t in july]
print(f"mean outdoor temp July 2023: {sum(jul_t) / len(jul_t):.1f} C")

# Free-floating check: indoor temperature with the AC off from 26 C on the hottest afternoon.
hot = max(july, key=lambda t: inp["temp"][t])
tin = SETPOINT_C
path = []
for t in range(hot - 4, hot + 20):
    tin = next_temp(b, tin, inp["temp"][t], inp["ghi"][t], 0.0)
    path.append(round(tin, 1))
print("AC-off indoor temp from", inp["time"][hot - 4], ":", path)
