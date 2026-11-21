
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from caregrid import sim

env_data = sim.load_inputs()
assets = sim.Assets()
buildings = sim.community()

t = 500
soc = 0.90
tin = [sim.SETPOINT_C] * len(buildings)

temp = env_data["temp"][t]
pv = sim.pv_kw(assets, env_data["poa"][t], temp)

batt_kwh = (soc - assets.soc_min) * assets.batt_kwh * assets.eta
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

rows = sim._demands(env_data, buildings, t, tin)

for value in [0.0, 0.5, 1.0]:
    proposal = [
        {
            "ess": value * row["ess"],
            "disc": value * row["disc"]
        }
        for row in rows
    ]

    decisions = sim.apply_shield(rows, ctx, proposal)

    print("\nAction:", value)

    for i, decision in enumerate(decisions):
        print(
            buildings[i].name,
            "Essential:", round(decision["ess"], 3),
            "Discretionary:", round(decision["disc"], 3),
            "Cooling:", round(decision["ac"], 3)
        )
print("\n--- ENERGY DIAGNOSTICS ---")
print("Outdoor temperature:", temp)
print("PV available:", round(pv, 3))
print("Battery available:", round(batt_kwh, 3), "kWh")
print("Battery power available:", round(batt_kw, 3), "kW")
print("Total supply:", round(ctx["supply"], 3), "kW")

print("Critical demand:", round(
    sum(sum(r["devices"]) for r in rows), 3
))

print("Essential demand:", round(
    sum(r["ess"] for r in rows), 3
))

print("Discretionary demand:", round(
    sum(r["disc"] for r in rows), 3
))

print("Cooling demand:", round(
    sum(r["ac"] for r in rows), 3
))

print("Safe cooling demand:", round(
    sum(r["safe_ac"] for r in rows), 3
))
print("\n--- SHIELD BUDGET DIAGNOSTIC ---")

critical_alloc, nc_budget = sim._shield_budget(rows, ctx)

print("Critical allocations:", critical_alloc)
print("Non-critical budget:", round(nc_budget, 4))

print("Cooling allocated:", round(sum(
    sim._thermal_shield_items(rows, ctx, nc_budget).get(
        f"{i:02d}a", 0.0
    )
    for i in range(len(rows))
), 4))