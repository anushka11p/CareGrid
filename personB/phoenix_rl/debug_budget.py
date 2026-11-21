
import os
import sys

ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
sys.path.insert(0, ROOT)

from personB.phoenix_rl.environment import PhoenixRLEnv
from caregrid import sim

env = PhoenixRLEnv()

obs, info = env.reset(
    seed=42,
    options={"start": 300, "duration": 24}
)

t = env.t
temp = env.inp["temp"][t]

pv = sim.pv_kw(
    env.assets,
    env.inp["poa"][t],
    temp
)

cap = env.assets.batt_kwh

batt_kwh = max(
    0.0,
    (env.soc - env.assets.soc_min)
    * cap * env.assets.eta
)

batt_kw = min(env.assets.batt_kw, batt_kwh)

ctx = {
    "t": t,
    "pv": pv,
    "soc": env.soc,
    "batt_kwh_avail": batt_kwh,
    "batt_kw_avail": batt_kw,
    "supply": pv + batt_kw,
    "forecast_end": env.start + env.duration,
    "w_heat": 1.0,
    "reserve_kwh": 0.0,
    "eta": env.assets.eta,
    "batt_kw": env.assets.batt_kw,
}

rows = sim._demands(
    env.inp, env.blds, t, env.tin
)

critical_alloc, nc_budget = sim._shield_budget(
    rows, ctx
)

thermal_alloc = sim._thermal_shield_items(
    rows, ctx, nc_budget
)

cooling_used = sum(
    thermal_alloc.get(f"{i:02d}a", 0.0)
    for i in range(len(rows))
)

print("\n========== SHIELD BUDGET ANALYSIS ==========")
print("PV:", pv)
print("Battery available kWh:", batt_kwh)
print("Battery available kW:", batt_kw)
print("Total supply:", ctx["supply"])
print("Critical devices allocated:", sum(critical_alloc.values()))
print("Non-critical budget:", nc_budget)
print("Cooling allocation:", cooling_used)
print("Budget remaining after cooling:", max(0.0, nc_budget - cooling_used))
print("Total safe cooling demand:", sum(r["safe_ac"] for r in rows))
print("Total essential demand:", sum(r["ess"] for r in rows))

env.close()
