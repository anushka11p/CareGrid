
import os
import sys
import numpy as np

ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
sys.path.insert(0, ROOT)

from personB.phoenix_rl.environment import PhoenixRLEnv
from caregrid import sim

env = PhoenixRLEnv()

for value in [0.0, 0.5, 1.0]:
    obs, info = env.reset(
        seed=42,
        options={"start": 300, "duration": 24}
    )

    action = np.full(
        env.action_space.shape,
        value,
        dtype=np.float32
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

    proposal = [
        {
            "ess": float(action[2*i]) * row["ess"],
            "disc": float(action[2*i+1]) * row["disc"]
        }
        for i, row in enumerate(rows)
    ]

    decisions = sim.apply_shield(rows, ctx, proposal)

    print("\nACTION:", value)
    print("PV:", pv)
    print("Battery available kW:", batt_kw)
    print("Supply:", ctx["supply"])

    for i, (row, p, d) in enumerate(
        zip(rows, proposal, decisions)
    ):
        print(
            f"Building {i+1}: "
            f"Requested ESS={p['ess']:.3f}, "
            f"Allocated ESS={d['ess']:.3f}, "
            f"Requested DISC={p['disc']:.3f}, "
            f"Allocated DISC={d['disc']:.3f}, "
            f"AC={d['ac']:.3f}"
        )

env.close()
print("\nSHIELD DEBUG COMPLETED")
