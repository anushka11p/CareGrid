"""Step 5: Phoenix outage environment for PPO-Lagrangian, built on caregrid.sim.

Fixes the issues in personB/phoenix_rl/environment.py:
  * the shield's battery reserve is on (Person B's environment set reserve_kwh = 0);
  * the agent sees the utility's 24 h restoration estimate, never the true outage length;
  * battery and indoor temperatures at outage start come from simulated grid-connected
    operation (or a 24 h pre-charge after a warning), not a fixed 90 % battery;
  * outages are sampled from many start days and four lengths, and testing uses unseen days;
  * the agent controls what matters for heat: how fast to spend energy above the reserve and
    which homes get extra cooling. Medical devices are never the agent's decision.

Action (10 numbers in [-1, 1]):
  release = ((a0 + 1) / 2) ** 2        share of energy above the reserve to spend this hour
  weights = softmax(2 * a[1:])         how extra cooling beyond the thermal floor is shared
Reward:  -sum_h w_h [T_h(t+1) - 26.7]+ / 20, w_h = health-twin vulnerability (or headcount)
Cost:    person-hours indoors above 32.2 C in the next hour
"""
import math

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from caregrid.health_twin import headcount, vulnerability
from caregrid.sim import (CAUTION_C, DANGER_C, Assets, OutageSim, _shield_parts, community, ctrl_rl,
                          load_inputs, pv_kw, run_normal)

OBS_DIM, ACT_DIM = 11 + 2 * 9, 10
TRAIN_DAYS, TEST_DAYS = tuple(range(1, 21)), tuple(range(21, 29))
DURATIONS = (12, 24, 48, 72)


def decode(a):
    a = np.clip(np.asarray(a, dtype=float), -1.0, 1.0)
    release = ((a[0] + 1.0) / 2.0) ** 2
    w = np.exp(2.0 * (a[1:] - a[1:].max()))
    return {"release": float(release), "weights": list(w / w.sum())}


class Shared:
    """Inputs computed once per process."""

    def __init__(self):
        self.inp = load_inputs()
        self.assets = Assets()
        self.blds = community()
        self.states, _ = run_normal(self.inp, self.assets, self.blds)
        self.pv_hist = [pv_kw(self.assets, p, t) for p, t in zip(self.inp["poa"], self.inp["temp"])]
        self._warned = {}

    def initial(self, start, warning):
        if not warning:
            return self.states[start]
        if start not in self._warned:
            soc, tin = self.states[start - 24]
            st, _ = run_normal(self.inp, self.assets, self.blds, t0=start - 24, t1=start,
                               soc0=soc, tin0=tin, precharge_from=start - 24)
            self._warned[start] = st[start]
        return self._warned[start]


def observation(sim, rows, ctx, shared):
    a, t, inp = shared.assets, sim.t, shared.inp
    _, q = _shield_parts(rows, ctx)
    hr = inp["hour"][t]
    pv_next = float(np.mean([shared.pv_hist[t + k - 24] for k in (1, 2, 3)]))
    temp_next = inp["temp"][min(t + 3, len(inp["temp"]) - 1)]
    head = [sim.soc, (t - sim.start) / 72.0, math.sin(2 * math.pi * hr / 24), math.cos(2 * math.pi * hr / 24),
            ctx["pv"] / a.pv_kwp, pv_next / a.pv_kwp, inp["temp"][t] / 50.0, temp_next / 50.0,
            ctx["reserve_kwh"] / a.batt_kwh, q["free_kwh"] / a.batt_kwh,
            max(0.0, ctx["forecast_end"] - t) / 24.0]
    tins = [(x - 26.0) / 10.0 for x in sim.sensed_tin]
    risks = [r["vuln_risk"] / 20.0 for r in rows]
    return np.asarray(head + tins + risks, dtype=np.float32)


class PhoenixOutageEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, days=TRAIN_DAYS, durations=DURATIONS, warning=False, shielded=True,
                 weighting="health_twin", p90_hours=48, forecast_hours=24, shared=None):
        super().__init__()
        self.s = shared or Shared()
        self.days, self.durations = list(days), list(durations)
        self.warning, self.shielded = warning, shielded
        self.weight = vulnerability if weighting == "health_twin" else headcount
        self.p90_hours, self.forecast_hours = p90_hours, forecast_hours
        self.action_space = spaces.Box(-1.0, 1.0, (ACT_DIM,), np.float32)
        self.observation_space = spaces.Box(-10.0, 10.0, (OBS_DIM,), np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        options = options or {}
        day = options.get("day", int(self.np_random.choice(self.days)))
        duration = options.get("duration", int(self.np_random.choice(self.durations)))
        start = 24 * day + 14
        soc0, tin0 = self.s.initial(start, self.warning)
        self.sim = OutageSim(self.s.inp, self.s.assets, self.s.blds, start, duration, soc0, tin0,
                             self.forecast_hours, self.p90_hours, shielded=self.shielded, pv_hist=self.s.pv_hist)
        self.rows, self.ctx = self.sim.observe()
        return observation(self.sim, self.rows, self.ctx, self.s), {}

    def step(self, action):
        dec = ctrl_rl(self.rows, self.ctx, decode(action), shielded=self.shielded)
        hour = self.sim.apply(self.rows, self.ctx, dec)
        reward = -sum(self.weight(b.name) * max(0.0, x - CAUTION_C) for b, x in zip(self.s.blds, self.sim.tin)) / 20.0
        cost = float(sum(b.residents * (x > DANGER_C) for b, x in zip(self.s.blds, self.sim.tin)))
        info = {"cost": cost, "devices_down": sum(h["devices_down"] for h in hour["buildings"])}
        done = self.sim.done
        if not done:
            self.rows, self.ctx = self.sim.observe()
            obs = observation(self.sim, self.rows, self.ctx, self.s)
        else:
            obs = np.zeros(OBS_DIM, dtype=np.float32)
        return obs, float(reward), done, False, info
