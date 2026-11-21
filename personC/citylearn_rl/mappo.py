"""Step 6: MAPPO-Lagrangian on CityLearn v3 (10 Austin homes), inside the CareGrid shield.

Each home is an agent. All agents share one actor network that sees only the agent's own home
(decentralised execution); a centralised critic sees every home during training (centralised
training). Per outage hour an agent chooses one number, rho in (0, 1): the share of its battery
energy above the medical reserve it may spend this hour. The shield in citylearn_port keeps
medical devices first and the reserve locked; the released budget then goes to essential
circuits and cooling exactly as the greedy shield does. Medical service is never an action.

Team reward: minus health-twin-weighted degree-hours above 26.7 C (CityLearn LSTM temperatures).
Cost: person-hours above 32.2 C, held below a limit with a Lagrange multiplier.
Training outages start 1-20 July 2018, test outages 21-28 July, 12/24/48/72 h, no warning.
Islanding uses the controller-layer workaround in citylearn_port/run_citylearn.py.

Run with the CityLearn environment:
    .venv-citylearn/bin/python personC/citylearn_rl/mappo.py --seeds 3 --episodes 400
"""
import argparse
import itertools
import math
import pathlib
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from caregrid.health_twin import Resident  # noqa: E402
from citylearn_port import run_citylearn as R  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
TRAIN_DAYS, TEST_DAYS, DURATIONS = tuple(range(1, 21)), tuple(range(21, 29)), (12, 24, 48, 72)
N, OBS = 10, 14

# Health twin for the CityLearn homes, consistent with each home's devices (medical.json).
RESIDENTS = {
    "home_01": [Resident(84, ("respiratory",))],
    "home_02": [Resident(78, ("diabetes",)), Resident(80, ("sleep_apnea",))],
    "home_03": [Resident(91, ("respiratory", "cognitive"))],
    "home_04": [Resident(72)],
    "home_05": [Resident(75, ("mobility",)), Resident(69)],
    "home_06": [Resident(88, ("diabetes", "sleep_apnea"))],
    "home_07": [Resident(81, ("respiratory", "cardiovascular"))],
    "home_08": [Resident(70), Resident(73, ("cardiovascular",))],
    "home_09": [Resident(86, ("respiratory",)), Resident(79, ("diabetes",))],
    "home_10": [Resident(83, ("respiratory",)), Resident(77, ("sleep_apnea",))],
}
VULN = {h: sum(r.score for r in rs) for h, rs in RESIDENTS.items()}


def fast_reserve(crit_by_hour, hours, pv, t, p90_end):
    """Same as citylearn_port.shield_reserve, vectorised: medical energy needed from t+1 to the
    worst-case end (at least 12 h), minus 70 % of solar 24 h earlier at the same hours."""
    horizon = max(12, p90_end - t)
    k = np.arange(1, horizon + 1)
    need = crit_by_hour[np.asarray(hours)[(t + k) % len(hours)]]
    idx = t + k - 24
    pv_f = np.where((idx >= 0) & (idx < len(pv)), 0.7 * pv[np.clip(idx, 0, len(pv) - 1)], 0.0)
    return float(np.maximum(0.0, need - pv_f).sum())


def shield_with_release(c, rho):
    """The greedy shield (citylearn_port.ctl_shield) with the release rate chosen by the agent."""
    on, budget = R._crit_first(c, c["supply"])
    crit_used = c["supply"] - budget
    from_batt = max(0.0, crit_used - c["pv"])
    free = max(0.0, c["batt_kwh"] - from_batt - c["reserve"])
    pv_left = max(0.0, c["pv"] - crit_used)
    deficit = max(0.0, c["reserve"] - (c["batt_kwh"] - from_batt))
    pv_left = max(0.0, pv_left - min(deficit / 0.9, c["batt_kw"]))
    batt_kw_left = max(0.0, c["batt_kw_avail"] - from_batt)
    nc = min(budget, pv_left + min(batt_kw_left, rho * free))
    a = R.greedy(R._items(c, False), nc)
    return on, a["e"], a["a"], free


def run_episode(day, duration, policy=None, controller="mappo"):
    """One outage. For 'mappo', `policy(local_obs[N, OBS], global_state) -> (rho[N], raw)`;
    otherwise any citylearn_port controller name (equal, rule, soft, shield, medical_only),
    run through this same loop so every controller gets the same metrics.
    Returns (metrics, transitions)."""
    fixed = R.CONTROLLERS.get(controller)
    start = R.JUL1 + (day - 1) * 24 + 14
    env, outage = R.make_env(start, duration)
    env.reset()
    blds = env.buildings
    hours = [[(h - 1) % 24 for h in b.energy_simulation.hour] for b in blds]
    pv = [np.asarray(b.pv.get_generation(b.energy_simulation.solar_generation)) for b in blds]
    plan = {b.name: {} for b in blds}
    crit = {b.name: np.array([R.crit_kw(b.name, h) for h in range(24)]) for b in blds}
    traj = []
    while not env.terminated:
        t = env.time_step
        islanded = t < len(outage) and outage[t]
        ctxs, obs = [], []
        for i, b in enumerate(blds):
            if not islanded:
                break
            es = b.energy_simulation
            nom = b.electrical_storage.nominal_power
            avail, soc = R.batt_avail_kwh(b, t)
            hr = hours[i][t]
            tin = es.indoor_dry_bulb_temperature[t - 1]
            c = {"t": t, "pv": float(pv[i][t]), "soc": soc, "batt_kwh": avail, "batt_kw": nom,
                 "batt_kw_avail": min(nom * 0.97, avail), "supply": float(pv[i][t]) + min(nom * 0.97, avail),
                 "devices": R.devices_at(b.name, hr), "ess": R.ESSENTIAL_KW, "cool": R.thermostat_kw(b, t),
                 "w_heat": 1.0, "risk": max(0.0, tin - R.CAUTION_C) / (R.DANGER_C - R.CAUTION_C) * R.MED[b.name]["residents"],
                 "forecast_end": R.WARM + R.FORECAST_H}
            c["reserve"] = (fast_reserve(crit[b.name], hours[i], pv[i], t, R.WARM + R.P90_H)
                            if controller in ("mappo", "shield") else 0.0)
            nxt = np.mean([pv[i][t + k - 24] for k in (1, 2, 3)])
            temp = b.weather.outdoor_dry_bulb_temperature[t]
            free = max(0.0, avail - c["reserve"])
            obs.append([soc, (t - R.WARM) / 72.0, math.sin(2 * math.pi * hr / 24), math.cos(2 * math.pi * hr / 24),
                        c["pv"] / 6.0, nxt / 6.0, temp / 50.0, (tin - 26.0) / 10.0, c["reserve"] / 13.5, free / 13.5,
                        max(0.0, c["forecast_end"] - t) / 24.0, VULN[b.name] / 5.0, sum(c["devices"]), c["cool"] / 5.0])
            ctxs.append(c)
        acts, rho = [], None
        if islanded and fixed is None:
            o = np.asarray(obs, dtype=np.float32)
            rho, extra = policy(o, o.reshape(-1))
            traj.append({"obs": o, "rho_raw": extra, "t": t})
        for i, b in enumerate(blds):
            es, bs = b.energy_simulation, b.electrical_storage
            nom = bs.nominal_power
            if islanded:
                c = ctxs[i]
                if fixed is None:
                    on, ess, cool, _ = shield_with_release(c, float(rho[i]))
                else:
                    on, ess, cool = fixed(c)
                served = sum(kw for kw, ok in zip(c["devices"], on) if ok) + ess + cool
                net = served - c["pv"]
                a_batt = -min(1.0, net / nom) if net > 0 else min(1.0, -net / nom)
                plan[b.name][t] = {"devices": c["devices"], "on": on, "ess_shed": R.ESSENTIAL_KW - ess,
                                   "crit_shed": sum(kw for kw, ok in zip(c["devices"], on) if not ok)}
            else:
                cool = R.thermostat_kw(b, t)
                load = es.non_shiftable_load[t] + cool - pv[i][t]
                soc = bs.soc[t - 1] if t > 0 else bs.initial_soc
                if load < 0:
                    a_batt = min(1.0, -load / nom)
                else:
                    a_batt = -min(1.0, load / nom, max(0.0, soc - R.RESERVE_GRID) * bs.capacity * 0.9 / nom)
            a_cool = -min(1.0, cool / b.cooling_device.nominal_power) if b.cooling_device.nominal_power > 0 else 0.0
            for an in b.active_actions:
                acts.append(a_cool if an == "cooling_or_heating_device" else a_batt if an == "electrical_storage" else 0.0)
        env.step([acts])
        if islanded and fixed is None:
            tin_now = [float(np.asarray(b.indoor_dry_bulb_temperature)[t]) for b in blds]
            traj[-1]["reward"] = -sum(VULN[b.name] * max(0.0, x - R.CAUTION_C) for b, x in zip(blds, tin_now)) / 20.0
            traj[-1]["cost"] = float(sum(R.MED[b.name]["residents"] * (x > R.DANGER_C) for b, x in zip(blds, tin_now)))

    m = {"crit_device_hours_down": 0, "crit_kwh_unserved": 0.0, "crit_kwh_demand": 0.0, "person_hours_danger": 0.0,
         "person_degree_hours": 0.0, "vuln_degree_hours": 0.0, "max_tin": 0.0, "infeasible_kwh": 0.0,
         "essential_kwh_unserved": 0.0}
    for b in blds:
        res = R.MED[b.name]["residents"]
        tin = np.asarray(b.indoor_dry_bulb_temperature)
        net = np.asarray(b.net_electricity_consumption)
        for t in range(R.WARM, R.WARM + duration):
            p = plan[b.name][t]
            extra = max(0.0, net[t] - p["crit_shed"] - p["ess_shed"] - 1e-3)
            m["infeasible_kwh"] += extra
            down = [not ok for ok in p["on"]]
            for j, kw in enumerate(p["devices"]):
                if not down[j] and extra > 1e-3:
                    down[j], extra = True, max(0.0, extra - kw)
            m["crit_device_hours_down"] += sum(down)
            m["crit_kwh_unserved"] += sum(kw for kw, d in zip(p["devices"], down) if d)
            m["crit_kwh_demand"] += sum(p["devices"])
            m["essential_kwh_unserved"] += p["ess_shed"]
            m["person_hours_danger"] += res * (tin[t] > R.DANGER_C)
            m["person_degree_hours"] += res * max(0.0, tin[t] - R.CAUTION_C)
            m["vuln_degree_hours"] += VULN[b.name] * max(0.0, tin[t] - R.CAUTION_C)
            m["max_tin"] = max(m["max_tin"], float(tin[t]))
    d = m["crit_kwh_demand"]
    m["crit_served_pct"] = 100.0 * (1 - m["crit_kwh_unserved"] / d) if d else 100.0
    return m, traj


def train(seed, episodes, eps_per_update=8):
    import torch
    import torch.nn as nn

    torch.set_num_threads(1)
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)

    def mlp(i, o):
        return nn.Sequential(nn.Linear(i, 64), nn.Tanh(), nn.Linear(64, 64), nn.Tanh(), nn.Linear(64, o))

    actor, v_r, v_c = mlp(OBS, 1), mlp(N * OBS, 1), mlp(N * OBS, 1)
    with torch.no_grad():
        actor[-1].bias.fill_(-2.5)                  # start near the fixed-pacing release (~1/24)
    log_std = nn.Parameter(torch.tensor([-0.5]))
    opt = torch.optim.Adam(list(actor.parameters()) + [log_std] + list(v_r.parameters()) + list(v_c.parameters()), lr=3e-4)
    lam, limit, log = 0.0, None, []

    def policy(o, g):
        with torch.no_grad():
            mu = actor(torch.as_tensor(o)).squeeze(-1)
            x = torch.distributions.Normal(mu, log_std.exp()).sample()
        return torch.sigmoid(x).numpy(), x.numpy()

    t0 = time.time()
    for upd in range(episodes // eps_per_update):
        batch = []
        for _ in range(eps_per_update):
            day, dur = int(rng.choice(TRAIN_DAYS)), int(rng.choice(DURATIONS))
            _, traj = run_episode(day, dur, policy)
            batch.append(traj)
        steps = [s for tr in batch for s in tr]
        mean_cost = float(np.mean([s["cost"] for s in steps]))
        if limit is None:
            limit = 0.8 * mean_cost                  # 80 % of the starting (near fixed-pacing) rate
        lam = max(0.0, lam + 0.05 * (mean_cost - limit))
        O, G, X, ADV, RR, RC = [], [], [], [], [], []
        for tr in batch:
            o = torch.as_tensor(np.stack([s["obs"] for s in tr]))
            g = o.reshape(len(tr), -1)
            with torch.no_grad():
                vr, vc = v_r(g).squeeze(-1).numpy(), v_c(g).squeeze(-1).numpy()
            r = np.array([s["reward"] for s in tr]); c = np.array([s["cost"] for s in tr])

            def gae(rew, val):
                adv, last = np.zeros(len(rew)), 0.0
                for k in reversed(range(len(rew))):
                    nv = val[k + 1] if k + 1 < len(rew) else 0.0
                    last = rew[k] + 0.99 * nv - val[k] + 0.99 * 0.95 * last
                    adv[k] = last
                return adv, adv + val
            ar, rr = gae(r, vr); ac, rc = gae(c, vc)
            O.append(o); G.append(g); X.append(np.stack([s["rho_raw"] for s in tr]))
            ADV.append((ar - lam * ac) / (1 + lam)); RR.append(rr); RC.append(rc)
        O = torch.cat(O); G = torch.cat(G)
        X = torch.as_tensor(np.concatenate(X), dtype=torch.float32)
        A = torch.as_tensor(np.concatenate(ADV), dtype=torch.float32)
        A = (A - A.mean()) / (A.std() + 1e-8)
        RR = torch.as_tensor(np.concatenate(RR), dtype=torch.float32); RC = torch.as_tensor(np.concatenate(RC), dtype=torch.float32)
        with torch.no_grad():
            old = torch.distributions.Normal(actor(O).squeeze(-1), log_std.exp()).log_prob(X)
        for _ in range(8):
            dist = torch.distributions.Normal(actor(O).squeeze(-1), log_std.exp())
            ratio = (dist.log_prob(X) - old).sum(-1).exp()        # joint ratio over the 10 agents
            pl = -torch.min(ratio * A, ratio.clamp(0.8, 1.2) * A).mean()
            vl = ((v_r(G).squeeze(-1) - RR) ** 2).mean() + ((v_c(G).squeeze(-1) - RC) ** 2).mean()
            loss = pl + 0.5 * vl
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(list(actor.parameters()) + list(v_r.parameters()) + list(v_c.parameters()), 0.5)
            opt.step()
        log.append({"seed": seed, "episodes": (upd + 1) * eps_per_update, "mean_reward": float(np.mean([s["reward"] for s in steps])),
                    "mean_cost": mean_cost, "cost_limit": limit, "lambda": lam,
                    "mean_release": float(torch.sigmoid(X).mean()), "minutes": (time.time() - t0) / 60})
    torch.save({"actor": actor.state_dict(), "log_std": log_std.detach()}, HERE / "models" / f"mappo_seed{seed}.pt")

    def greedy_policy(o, g):
        with torch.no_grad():
            return torch.sigmoid(actor(torch.as_tensor(o)).squeeze(-1)).numpy(), None

    rows = []
    for day, dur in itertools.product(TEST_DAYS, DURATIONS):
        m, _ = run_episode(day, dur, greedy_policy)
        rows.append({"controller": "mappo_shield", "seed": seed, "day": day, "duration_h": dur, **m})
    return rows, log


def fixed_pacing(day, dur):
    """The greedy shield expressed as a release rate (1/remaining hours), through the same code
    path as MAPPO; must reproduce citylearn_port's 'shield' controller."""
    def pol(o, g):
        rem = np.maximum(1.0, o[:, 10] * 24.0)
        return 1.0 / rem, None
    m, _ = run_episode(day, dur, pol)
    return {"controller": "shield_fixed_pacing", "seed": 0, "day": day, "duration_h": dur, **m}


def baseline(args):
    ctrl, day, dur = args
    if ctrl == "shield_fixed_pacing":
        return fixed_pacing(day, dur)
    m, _ = run_episode(day, dur, controller=ctrl)
    return {"controller": ctrl, "seed": 0, "day": day, "duration_h": dur, **m}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--episodes", type=int, default=400)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    (HERE / "models").mkdir(exist_ok=True)
    (HERE / "results").mkdir(exist_ok=True)
    t0 = time.time()
    with Pool(args.workers) as pool:
        base = pool.map(baseline, list(itertools.product(["soft", "shield", "medical_only", "shield_fixed_pacing"],
                                                         TEST_DAYS, DURATIONS)), chunksize=4)
        res = pool.starmap(train, [(s, args.episodes) for s in range(args.seeds)])
    pd.DataFrame(base + [r for ev, _ in res for r in ev]).to_csv(HERE / "results" / "eval.csv", index=False)
    pd.DataFrame([r for _, lg in res for r in lg]).to_csv(HERE / "results" / "training.csv", index=False)
    print(f"done in {(time.time() - t0) / 60:.1f} min")
