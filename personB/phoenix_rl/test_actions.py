
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from personB.phoenix_rl.environment import PhoenixRLEnv
import numpy as np


def run_action(value):
    env = PhoenixRLEnv(duration=24, start=300)
    env.reset()

    action = np.full(
        env.action_space.shape,
        value,
        dtype=np.float32
    )

    total_reward = 0.0
    total_cost = 0.0

    for _ in range(24):
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        total_cost += info["constraint_cost"]

    return total_reward, total_cost, env.soc


for value in [0.0, 0.5, 1.0]:
    reward, cost, soc = run_action(value)

    print(
        f"Action={value:.1f} | "
        f"Reward={reward:.3f} | "
        f"Constraint={cost:.3f} | "
        f"Final SOC={soc:.3f}"
    )
