
import sys
import csv
from pathlib import Path

import numpy as np
import gymnasium as gym

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from personB.phoenix_rl.environment import PhoenixRLEnv


# ==================================================
# CONFIGURATION
# ==================================================

TOTAL_TIMESTEPS = 10000      
EPISODE_LENGTH = 24
START = 300

LEARNING_RATE = 3e-4
SEED = 42

# Provisional episode-level cost limits.
# These must be calibrated using baseline simulations.
MEDICAL_COST_LIMIT = 0.0
THERMAL_COST_LIMIT = 100.0

DUAL_LEARNING_RATE = 0.0001
INITIAL_MEDICAL_LAMBDA = 0.1
INITIAL_THERMAL_LAMBDA = 0.1

MAX_LAMBDA = 100.0


# ==================================================
# SHARED LAGRANGE MULTIPLIERS
# ==================================================

class LagrangeState:

    def __init__(self):
        self.medical_lambda = INITIAL_MEDICAL_LAMBDA
        self.thermal_lambda = INITIAL_THERMAL_LAMBDA


# ==================================================
# TWO-CONSTRAINT REWARD WRAPPER
# ==================================================

class TwoConstraintWrapper(gym.Wrapper):

    def __init__(self, env, lagrange_state):
        super().__init__(env)

        self.lagrange_state = lagrange_state

        self.episode_medical_cost = 0.0
        self.episode_thermal_cost = 0.0

    def reset(self, **kwargs):

        self.episode_medical_cost = 0.0
        self.episode_thermal_cost = 0.0

        return self.env.reset(**kwargs)

    def step(self, action):

        obs, reward, terminated, truncated, info = (
            self.env.step(action)
        )

        medical_cost = float(
            info["medical_constraint_cost"]
        )

        thermal_cost = float(
            info["thermal_constraint_cost"]
        )

        self.episode_medical_cost += medical_cost
        self.episode_thermal_cost += thermal_cost

        adjusted_reward = (
            float(reward)
            - self.lagrange_state.medical_lambda * medical_cost
            - self.lagrange_state.thermal_lambda * thermal_cost
        )

        if terminated or truncated:

            info["episode_medical_cost"] = (
                self.episode_medical_cost
            )

            info["episode_thermal_cost"] = (
                self.episode_thermal_cost
            )

        return (
            obs,
            adjusted_reward,
            terminated,
            truncated,
            info
        )


# ==================================================
# LAGRANGE MULTIPLIER UPDATE CALLBACK
# ==================================================

class TwoConstraintCallback(BaseCallback):

    def __init__(self, lagrange_state, verbose=1):

        super().__init__(verbose)

        self.lagrange_state = lagrange_state

        self.medical_history = []
        self.thermal_history = []

        self.medical_lambda_history = []
        self.thermal_lambda_history = []

    def _on_step(self):

        for done, info in zip(
            self.locals["dones"],
            self.locals["infos"]
        ):

            if done:

                medical_cost = float(
                    info.get("episode_medical_cost", 0.0)
                )

                thermal_cost = float(
                    info.get("episode_thermal_cost", 0.0)
                )

                self.medical_history.append(medical_cost)
                self.thermal_history.append(thermal_cost)

                # Independent dual ascent updates.
                medical_violation = (
                    medical_cost - MEDICAL_COST_LIMIT
                )

                thermal_violation = (
                    thermal_cost - THERMAL_COST_LIMIT
                )

                self.lagrange_state.medical_lambda = float(
                    np.clip(
                        self.lagrange_state.medical_lambda
                        + DUAL_LEARNING_RATE * medical_violation,
                        0.0,
                        MAX_LAMBDA
                    )
                )

                self.lagrange_state.thermal_lambda = float(
                    np.clip(
                        self.lagrange_state.thermal_lambda
                        + DUAL_LEARNING_RATE * thermal_violation,
                        0.0,
                        MAX_LAMBDA
                    )
                )

                self.medical_lambda_history.append(
                    self.lagrange_state.medical_lambda
                )

                self.thermal_lambda_history.append(
                    self.lagrange_state.thermal_lambda
                )

                if self.verbose:

                    print(
                        f"Medical cost: {medical_cost:.3f} | "
                        f"Thermal cost: {thermal_cost:.3f} | "
                        f"Medical lambda: "
                        f"{self.lagrange_state.medical_lambda:.5f} | "
                        f"Thermal lambda: "
                        f"{self.lagrange_state.thermal_lambda:.5f}"
                    )

        return True


# ==================================================
# TRAINING
# ==================================================

def main():

    print("Creating Phoenix environment...")

    base_env = PhoenixRLEnv(
        duration=EPISODE_LENGTH,
        start=START
    )

    lagrange_state = LagrangeState()

    env = TwoConstraintWrapper(
        base_env,
        lagrange_state
    )

    env = Monitor(env)

    callback = TwoConstraintCallback(lagrange_state)

    print("Creating PPO model...")

    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=LEARNING_RATE,
        n_steps=EPISODE_LENGTH,
        batch_size=24,
        gamma=0.99,
        gae_lambda=0.95,
        ent_coef=0.01,
        verbose=1,
        seed=SEED,
        device="cpu"
    )

    print("Starting two-constraint PPO-Lagrangian training...")

    model.learn(
        total_timesteps=TOTAL_TIMESTEPS,
        callback=callback
    )

    # ==================================================
    # SAVE RESULTS
    # ==================================================

    output = (
    Path(__file__).resolve().parent
    / "models"
    / "two_constraint_10k"
    )

    output.mkdir(parents=True, exist_ok=True)

    model.save(
        str(output / "phoenix_two_constraint_ppo")
    )

    np.save(
        output / "medical_cost_history.npy",
        np.asarray(callback.medical_history)
    )

    np.save(
        output / "thermal_cost_history.npy",
        np.asarray(callback.thermal_history)
    )

    np.save(
        output / "medical_lambda_history.npy",
        np.asarray(callback.medical_lambda_history)
    )

    np.save(
        output / "thermal_lambda_history.npy",
        np.asarray(callback.thermal_lambda_history)
    )

    with open(
        output / "training_history.csv",
        "w",
        newline=""
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "episode",
            "medical_cost",
            "thermal_cost",
            "medical_lambda",
            "thermal_lambda"
        ])

        for i in range(len(callback.medical_history)):

            writer.writerow([
                i + 1,
                callback.medical_history[i],
                callback.thermal_history[i],
                callback.medical_lambda_history[i],
                callback.thermal_lambda_history[i]
            ])

    print("\nTwo-constraint training completed.")

    print(
        "Final medical lambda:",
        lagrange_state.medical_lambda
    )

    print(
        "Final thermal lambda:",
        lagrange_state.thermal_lambda
    )

    print("Episodes recorded:", len(callback.medical_history))
    print("Medical constraint limit:", MEDICAL_COST_LIMIT)
    print("Thermal constraint limit:", THERMAL_COST_LIMIT)
    print("Training timesteps:", TOTAL_TIMESTEPS)
    print("Random seed:", SEED)

    print("Saved outputs:", output)


if __name__ == "__main__":
    main()
