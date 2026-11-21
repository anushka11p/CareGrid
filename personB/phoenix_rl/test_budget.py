
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from caregrid import sim

inp = sim.load_inputs()
assets = sim.Assets()
blds = sim.community()

soc = 0.90
tin = [sim.SETPOINT_C] * len(blds)

print("Hour | PV | Supply | Critical | Safe cooling | NC budget")

for t in range(0, 840, 12):
    temp = inp["temp"][t]
    pv = sim.pv_kw(assets, inp["poa"][t], temp)

    batt_kwh = max(
        0.0,
        (soc - assets.soc_min) * assets.batt_kwh * assets.eta
    )
    batt_kw = min(assets.batt_kw, batt_kwh)

    ctx = {
        "t": t,
        "pv": pv,
        "soc": soc,
        "batt_kwh_avail": batt_kwh,
        "batt_kw_avail": batt_kw,
        "supply": pv + batt_kw,
        "forecast_end": t + 24,
        "w_heat": 1.0,
        "reserve_kwh": 0.0,
        "eta": assets.eta,
        "batt_kw": assets.batt_kw,
    }

    rows = sim._demands(inp, blds, t, tin)
    _, budget = sim._shield_budget(rows, ctx)

    cooling = sum(r["safe_ac"] for r in rows)
    critical = sum(sum(r["devices"]) for r in rows)

    print(
        f"{t:4d} | {pv:5.2f} | {ctx['supply']:6.2f} | "
        f"{critical:8.2f} | {cooling:12.2f} | {budget:9.2f}"
    )

