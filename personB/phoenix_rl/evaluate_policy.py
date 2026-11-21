
import sys
from pathlib import Path

import numpy as np
from stable_baselines3 import PPO

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from personB.phoenix_rl.environment import PhoenixRLEnv


# --------------------------------------------------
# Configuration
# --------------------------------------------------

EPISODE_LENGTH = 24
START = 300

MODEL_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "phoenix_ppo_lagrangian.zip"
)


# --------------------------------------------------
# Evaluation function
# --------------------------------------------------

def evaluate_policy(name, model=None, fixed_action=None):

    env = PhoenixRLEnv(
        duration=EPISODE_LENGTH,
        start=START
    )

    obs, info = env.reset(seed=42)

    total_reward = 0.0
    total_constraint = 0.0
    total_medical_down = 0
    total_danger_people = 0

    terminated = False
    truncated = False

    while not (terminated or truncated):

        if model is not None:
            action, _ = model.predict(
                obs,
                deterministic=True
            )
        else:
            action = np.full(
                env.action_space.shape,
                fixed_action,
                dtype=np.float32
            )

        obs, reward, terminated, truncated, info = (
            env.step(action)
        )

        total_reward += reward
        total_constraint += info["constraint_cost"]
        total_medical_down += info["medical_devices_down"]
        total_danger_people += info["danger_people"]

    final_soc = info["battery_soc"]

    env.close()

    return {
        "Controller": name,
        "Reward": round(total_reward, 3),
        "Constraint cost": round(total_constraint, 3),
        "Medical downtime": total_medical_down,
        "Danger person-hours": total_danger_people,
        "Final battery SOC": round(final_soc, 3)
    }


# --------------------------------------------------
# Run evaluation
# --------------------------------------------------

def main():

    print("Loading trained PPO-Lagrangian model...")

    model = PPO.load(
        str(MODEL_PATH),
        device="cpu"
    )

    results = []

    print("\nEvaluating fixed-action baselines...")

    results.append(
        evaluate_policy("Fixed 0.0", fixed_action=0.0)
    )

    results.append(
        evaluate_policy("Fixed 0.5", fixed_action=0.5)
    )

    results.append(
        evaluate_policy("Fixed 1.0", fixed_action=1.0)
    )

    print("\nEvaluating PPO-Lagrangian...")

    results.append(
        evaluate_policy(
            "PPO-Lagrangian",
            model=model
        )
    )

    print("\n========== EVALUATION RESULTS ==========\n")

    headers = list(results[0].keys())

    print(" | ".join(headers))
    print("-" * 105)

    for result in results:
        print(
            " | ".join(str(result[key]) for key in headers)
        )

    output = Path(__file__).resolve().parent / "results"
    output.mkdir(exist_ok=True)

    import csv

    with open(
        output / "phoenix_policy_comparison.csv",
        "w",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=headers
        )

        writer.writeheader()
        writer.writerows(results)

    print("\nResults saved to:", output)


if __name__ == "__main__":
    main()
