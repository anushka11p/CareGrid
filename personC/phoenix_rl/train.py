"""Step 5: train PPO-Lagrangian (Stable-Baselines3 PPO + Lagrange multiplier on the cost, the
same approach as Person B) inside the shield, then evaluate on unseen outages.

Configurations (5 seeds each):
  nowarn          shielded, health-twin reward, battery as found at outage start
  warn            shielded, health-twin reward, 24 h warning (battery pre-charged)
  warn_uniform    as warn, every resident weighted 1 (health-twin ablation, Step 7)
  nowarn_noshield reserve and refill switched off (shield ablation, Step 7)
  warn_noshield   as above with a warning
Writes personC/phoenix_rl/results/{eval,training,baselines}.csv and models/*.zip.
"""
import argparse
import itertools
import pathlib
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
HERE = ROOT / "personC" / "phoenix_rl"

CONFIGS = {
    "nowarn": dict(warning=False, shielded=True, weighting="health_twin"),
    "warn": dict(warning=True, shielded=True, weighting="health_twin"),
    "warn_uniform": dict(warning=True, shielded=True, weighting="headcount"),
    "nowarn_noshield": dict(warning=False, shielded=False, weighting="health_twin"),
    "warn_noshield": dict(warning=True, shielded=False, weighting="health_twin"),
}
COST_LIMIT_SHARE = 0.8      # constraint: 80 % of the fixed-pacing shield's dangerous-heat rate


def fixed_pacing_cost(env, episodes=40):
    """Mean cost per hour of the fixed-pacing shield on training outages (sets the limit)."""
    from personC.phoenix_rl.env import ACT_DIM
    costs = []
    for _ in range(episodes):
        env.reset()
        done = False
        while not done:
            rem = max(1.0, env.ctx["forecast_end"] - env.ctx["t"])
            a = np.zeros(ACT_DIM, dtype=np.float32)
            a[0] = 2.0 * np.sqrt(1.0 / rem) - 1.0           # release = 1 / remaining hours
            _, _, done, _, info = env.step(a)
            costs.append(info["cost"])
    return float(np.mean(costs))


def train(config, seed, steps):
    import gymnasium as gym
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from personC.phoenix_rl.env import PhoenixOutageEnv, Shared

    torch.set_num_threads(1)
    shared = Shared()
    env = PhoenixOutageEnv(shared=shared, **CONFIGS[config])
    env.reset(seed=seed)
    limit = COST_LIMIT_SHARE * fixed_pacing_cost(env)
    state = {"lam": 0.0, "costs": []}

    class Lagrangian(gym.Wrapper):
        def step(self, action):
            obs, r, term, trunc, info = self.env.step(action)
            state["costs"].append(info["cost"])
            return obs, r - state["lam"] * info["cost"] / 20.0, term, trunc, info

    log = []

    class UpdateLambda(BaseCallback):
        def _on_rollout_end(self):
            c = float(np.mean(state["costs"])) if state["costs"] else 0.0
            state["lam"] = max(0.0, state["lam"] + 0.05 * (c - limit))
            log.append({"config": config, "seed": seed, "steps": self.num_timesteps, "mean_cost": c,
                        "cost_limit": limit, "lambda": state["lam"]})
            state["costs"].clear()

        def _on_step(self):
            return True

    model = PPO("MlpPolicy", Lagrangian(env), n_steps=2048, batch_size=256, learning_rate=3e-4,
                gamma=0.99, gae_lambda=0.95, ent_coef=0.0, seed=seed, verbose=0,
                policy_kwargs=dict(net_arch=[64, 64]))
    model.learn(total_timesteps=steps, callback=UpdateLambda())
    (HERE / "models").mkdir(exist_ok=True)
    model.save(HERE / "models" / f"{config}_seed{seed}")
    return model, log, shared


def evaluate(config, seed, model, shared):
    from caregrid.sim import metrics, run_outage
    from personC.phoenix_rl.env import DURATIONS, TEST_DAYS, decode, observation

    cfg = CONFIGS[config]
    controller = "rl_shield" if cfg["shielded"] else "rl_noreserve"

    def policy(sim, rows, ctx):
        a, _ = model.predict(observation(sim, rows, ctx, shared), deterministic=True)
        return decode(a)

    out = []
    for day, dur in itertools.product(TEST_DAYS, DURATIONS):
        start = 24 * day + 14
        soc0, tin0 = shared.initial(start, cfg["warning"])
        m = metrics(run_outage(shared.inp, shared.assets, shared.blds, start, dur, controller, soc0, tin0,
                               policy=policy), shared.blds)
        out.append({"controller": config, "seed": seed, "warning": cfg["warning"], "day": day, "duration_h": dur, **m})
    return out


def job(args):
    config, seed, steps = args
    model, log, shared = train(config, seed, steps)
    return evaluate(config, seed, model, shared), log


def baseline_job(args):
    """Fixed controllers on the same test outages."""
    controller, warning, release = args
    from caregrid.oracle import run_oracle
    from caregrid.sim import metrics, run_outage
    from personC.phoenix_rl.env import DURATIONS, TEST_DAYS, Shared

    s = Shared()
    out = []
    for day, dur in itertools.product(TEST_DAYS, DURATIONS):
        start = 24 * day + 14
        soc0, tin0 = s.initial(start, warning)
        if controller == "oracle":
            m = run_oracle(s.inp, s.assets, s.blds, start, dur, soc0, tin0)
        elif controller == "fixed_release":
            pol = lambda sim, rows, ctx: {"release": release, "weights": [1 / 9] * 9}  # noqa: E731
            m = metrics(run_outage(s.inp, s.assets, s.blds, start, dur, "rl_shield", soc0, tin0, policy=pol), s.blds)
        else:
            m = metrics(run_outage(s.inp, s.assets, s.blds, start, dur, controller, soc0, tin0), s.blds)
        name = f"fixed_release_{release}" if controller == "fixed_release" else controller
        out.append({"controller": name, "seed": 0, "warning": warning, "day": day, "duration_h": dur, **m})
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=300_000)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--configs", default=",".join(CONFIGS))
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    (HERE / "results").mkdir(exist_ok=True)
    t0 = time.time()
    jobs = [(c, s, args.steps) for c in args.configs.split(",") for s in range(args.seeds)]
    bjobs = [(c, w, None) for c in ("soft", "shield", "mpc_shield", "oracle") for w in (False, True)]
    bjobs += [("fixed_release", w, r) for w in (False, True) for r in (0.02, 0.05, 0.1, 0.3, 1.0)]
    with Pool(args.workers) as pool:
        base = pool.map(baseline_job, bjobs)
        res = pool.map(job, jobs)
    pd.DataFrame([r for b in base for r in b]).to_csv(HERE / "results" / "baselines.csv", index=False)
    pd.DataFrame([r for e, _ in res for r in e]).to_csv(HERE / "results" / "eval.csv", index=False)
    pd.DataFrame([r for _, lg in res for r in lg]).to_csv(HERE / "results" / "training.csv", index=False)
    print(f"{len(jobs)} training runs + {len(bjobs)} baseline sets in {(time.time() - t0) / 60:.1f} min")
