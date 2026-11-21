
import os
import sys
import numpy as np

ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
sys.path.insert(0, ROOT)

from personB.phoenix_rl.environment import PhoenixRLEnv

env = PhoenixRLEnv()

print("\n========== ACTION SENSITIVITY TEST ==========")

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

    print(f"\nTesting action value: {value}")

    for step in range(3):
        obs, reward, terminated, truncated, info = env.step(action)

        print(
            f"Step {step + 1}: "
            f"Reward={reward:.3f}, "
            f"Medical cost={info.get('medical_constraint_cost', 0):.3f}, "
            f"Thermal cost={info.get('thermal_constraint_cost', 0):.3f}, "
            f"SOC={info.get('battery_soc', 0):.3f}"
        )

        if terminated or truncated:
            break

env.close()

print("\n========== TEST COMPLETED ==========")
