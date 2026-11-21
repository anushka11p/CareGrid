
import os
import sys
import numpy as np
import pandas as pd
from stable_baselines3 import PPO

# Import Person A's simulator and Person B's environment
ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
sys.path.insert(0, ROOT)

from personB.phoenix_rl.environment import PhoenixRLEnv


EPISODE_LENGTH = 24
START = 300
SEED = 42

MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "models",
    "two_constraint_10k",
    "phoenix_two_constraint_ppo.zip"
)
RESULTS_DIR = os.path.join(
    os.path.dirname(__file__), "results"
)
os.makedirs(RESULTS_DIR, exist_ok=True)


def evaluate_policy(name, env, action=None, model=None):
    obs, info = env.reset(
        seed=SEED,
        options={
            "start": START,
            "duration": EPISODE_LENGTH
        }
    )

    totals = {
        "reward": 0.0,
        "medical_cost": 0.0,
        "thermal_cost": 0.0,
        "medical_devices_down": 0.0,
        "danger_person_hours": 0.0,
        "danger_degree_hours": 0.0,
    }

    for step in range(EPISODE_LENGTH):
        if model is not None:
            chosen_action, _ = model.predict(
                obs, deterministic=True
            )
        else:
            chosen_action = np.full(
                env.action_space.shape,
                action,
                dtype=np.float32
            )

        obs, reward, terminated, truncated, info = env.step(
            chosen_action
        )

        totals["reward"] += float(reward)
        totals["medical_cost"] += float(
            info.get("medical_constraint_cost", 0)
        )
        totals["thermal_cost"] += float(
            info.get("thermal_constraint_cost", 0)
        )
        totals["medical_devices_down"] += float(
            info.get("medical_devices_down", 0)
        )
        totals["danger_person_hours"] += float(
            info.get("danger_people", 0)
        )
        totals["danger_degree_hours"] += float(
            info.get("danger_degree_hours", 0)
        )

        if terminated or truncated:
            break

    totals["controller"] = name
    totals["final_battery_soc"] = float(
        info.get("battery_soc", np.nan)
    )

    return totals


def main():
    env = PhoenixRLEnv()

    print("Loading two-constraint PPO-Lagrangian model...")
    model = PPO.load(MODEL_PATH)

    results = []

    print("\nEvaluating fixed-action baselines...")
    for value in [0.0, 0.5, 1.0]:
        print(f"Testing fixed action: {value}")
        results.append(
            evaluate_policy(
                f"fixed_{value}",
                env,
                action=value
            )
        )

    print("\nEvaluating trained PPO-Lagrangian...")
    results.append(
        evaluate_policy(
            "two_constraint_ppo_lagrangian",
            env,
            model=model
        )
    )

    df = pd.DataFrame(results)

    output_path = os.path.join(
        RESULTS_DIR,
        "two_constraint_policy_comparison.csv"
    )

    df.to_csv(output_path, index=False)

    print("\n========== EVALUATION RESULTS ==========")
    print(df.to_string(index=False))

    print("\nResults saved to:")
    print(output_path)

    env.close()


if __name__ == "__main__":
    main()
