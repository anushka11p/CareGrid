
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from personB.phoenix_rl.environment import PhoenixRLEnv
import numpy as np

env = PhoenixRLEnv(duration=24)
obs, info = env.reset()

total_reward = 0
total_cost = 0
total_down = 0
total_danger = 0

done = False
steps = 0

while not done:
    action = np.ones(
        env.action_space.shape,
        dtype=np.float32
    )

    obs, reward, terminated, truncated, info = env.step(action)

    total_reward += reward
    total_cost += info["constraint_cost"]
    total_down += info["medical_devices_down"]
    total_danger += info["danger_people"]

    done = terminated or truncated
    steps += 1

print("\n--- 24-HOUR PHOENIX TEST ---")
print("Episode hours:", steps)
print("Total reward:", round(total_reward, 3))
print("Total constraint cost:", round(total_cost, 3))
print("Medical device downtime:", total_down)
print("Danger person-hours:", total_danger)
print("Final battery SOC:", round(env.soc, 3))
