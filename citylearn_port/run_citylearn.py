"""CareGrid outage experiment on CityLearn v3 (tx_travis_county_neighborhood).

CityLearn supplies the building physics: per-home LSTM indoor-temperature models, heat-pump
COP, battery model (power-dependent efficiency, losses), measured 2018 Austin weather and
real ResStock home loads. Each home is its own island: 6 kW PV + 13.5 kWh / 5 kW battery.

Islanding is enforced in this controller layer, not by CityLearn's built-in outage mode,
because CityLearn 3.0.2 prevents batteries from discharging during outages (its local-load
estimate is taken before loads are energised and is net of PV, so it is zero). Here CityLearn
runs grid-connected and, during outage hours, every controller may only serve load from
PV + battery; any grid import CityLearn still records is counted as unserved energy.

During an outage each home runs on a critical-loads panel: 0.35 kW essential circuits plus
its medical devices, with the electric water heater off (identical for every controller).
"""
import argparse
import itertools
import json
import pathlib
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DS = ROOT / "data" / "citylearn" / "caregrid_travis"
OUT = ROOT / "results" / "citylearn"
MED = json.loads((DS / "medical.json").read_text())

JUL1 = 181 * 24                  # index of 2018-07-01 00:00 in the annual hourly series
WARM = 48                        # grid-connected hours simulated before each outage
ESSENTIAL_KW = 0.35
CAUTION_C, DANGER_C = 26.7, 32.2
W_CRITICAL, W_ESSENTIAL = 10.0, 2.0
SOC_MIN, RESERVE_GRID = 0.10, 0.30
FORECAST_H, P90_H = 24, 48


def make_env(start, duration, batt_kwh=13.5, batt_kw=5.0):
    from citylearn.citylearn import CityLearnEnv
    s = json.loads((DS / "schema.json").read_text())
    s["root_directory"] = str(DS)
    s["central_agent"] = True
    s["simulation_start_time_step"] = start - WARM
    s["simulation_end_time_step"] = start + duration
    for b in s["buildings"].values():
        b["power_outage"]["simulate_power_outage"] = False
        b["electrical_storage"]["attributes"].update(capacity=batt_kwh, nominal_power=batt_kw)
    env = CityLearnEnv(s)
    outage = np.zeros(WARM + duration + 1, dtype=bool)
    outage[WARM:WARM + duration] = True
    for b in env.buildings:
        es = b.energy_simulation
        hod = (np.asarray(es.hour[:len(outage)]) - 1) % 24
        crit = np.array([MED[b.name]["critical_kw_by_hour"][h] for h in hod])
        nsl = np.asarray(es.non_shiftable_load)
        nsl[:len(outage)][outage] = ESSENTIAL_KW + crit[outage]   # critical-loads panel while islanded
        np.asarray(es.dhw_demand)[:len(outage)][outage] = 0.0      # water heater is not on that panel
    return env, outage


# ------------------------------------------------------------------ helpers
def devices_at(name, hour):
    return sorted(d["kw"] for d in MED[name]["devices"] if not d["hours"] or hour in d["hours"])


def crit_kw(name, hour):
    return sum(devices_at(name, hour))


def thermostat_kw(b, t):
    """Electric kW a normal thermostat would ask for: the dataset's ideal load, plus
    recovery effort while the home is above its cooling set point."""
    es = b.energy_simulation
    temp = b.weather.outdoor_dry_bulb_temperature[t]
    cop = b.cooling_device.get_cop(temp, heating=False)
    ideal = es.cooling_demand_without_control[t] / max(cop, 1e-6)
    tin = es.indoor_dry_bulb_temperature[t - 1] if t > 0 else es.indoor_dry_bulb_temperature[0]
    extra = max(0.0, tin - es.indoor_dry_bulb_temperature_cooling_set_point[t]) * 0.5 * b.cooling_device.nominal_power
    if es.hvac_mode[t] not in (1, 3):
        return 0.0
    return float(min(b.cooling_device.nominal_power, ideal + extra))


def batt_avail_kwh(b, t):
    bs = b.electrical_storage
    soc = bs.soc[t - 1] if t > 0 else bs.initial_soc
    return max(0.0, (soc - SOC_MIN) * bs.capacity * bs.efficiency * 0.97), soc


def greedy(items, budget):
    alloc = {}
    for value, key, kw, divisible in sorted(items, key=lambda x: (-x[0], x[1])):
        if kw <= budget + 1e-9:
            alloc[key], budget = kw, budget - kw
        elif divisible and budget > 1e-9:
            alloc[key], budget = budget, 0.0
        else:
            alloc[key] = 0.0
    return alloc


# ------------------------------------------------------------------ outage controllers
# Each returns (devices_on: list[bool], essential_kw, cooling_kw) for one home and hour.
def ctl_equal(c):
    demand = sum(c["devices"]) + c["ess"] + c["cool"]
    f = 1.0 if demand <= 1e-9 else min(1.0, c["supply"] / demand)
    return [f >= 1 - 1e-9] * len(c["devices"]), f * c["ess"], f * c["cool"]


def _crit_first(c, budget):
    on = []
    for kw in c["devices"]:
        ok = kw <= budget + 1e-9
        on.append(ok)
        budget -= kw if ok else 0.0
    return on, budget


def ctl_rule(c):
    on, budget = _crit_first(c, c["supply"])
    ess = min(c["ess"], budget)
    budget -= ess
    used = c["supply"] - budget
    flex = budget if c["soc"] > 0.40 else max(0.0, min(budget, c["pv"] - used))
    return on, ess, min(c["cool"], flex)


def _items(c, include_crit):
    items = [(W_ESSENTIAL, "e", c["ess"], True), (c["w_heat"] * c["risk"], "a", c["cool"], True)]
    if include_crit:
        items += [(W_CRITICAL, f"d{j}", kw, False) for j, kw in enumerate(c["devices"])]
    return items


def ctl_soft(c):
    remaining = max(1.0, c["forecast_end"] - c["t"])
    paced = min(c["supply"], c["pv"] + min(c["batt_kw_avail"], c["batt_kwh"] / remaining))
    budget = max(paced, min(c["supply"], sum(c["devices"])))
    a = greedy(_items(c, True), budget)
    return [a.get(f"d{j}", 0) >= kw - 1e-9 for j, kw in enumerate(c["devices"])], a["e"], a["a"]


def ctl_shield(c):
    on, budget = _crit_first(c, c["supply"])
    crit_used = c["supply"] - budget
    from_batt = max(0.0, crit_used - c["pv"])
    free = max(0.0, c["batt_kwh"] - from_batt - c["reserve"])
    pv_left = max(0.0, c["pv"] - crit_used)
    deficit = max(0.0, c["reserve"] - (c["batt_kwh"] - from_batt))
    pv_left = max(0.0, pv_left - min(deficit / 0.9, c["batt_kw"]))
    batt_kw_left = max(0.0, c["batt_kw_avail"] - from_batt)
    remaining = max(1.0, c["forecast_end"] - c["t"])
    nc = min(budget, pv_left + min(batt_kw_left, free / remaining))
    a = greedy(_items(c, False), nc)
    return on, a["e"], a["a"]


def ctl_medical_only(c):
    """Physical bound for medical service: energy goes to medical devices and nothing else,
    so no controller can keep more device-hours powered with the same PV and battery."""
    on, _ = _crit_first(c, c["supply"])
    return on, 0.0, 0.0


CONTROLLERS = {"equal": ctl_equal, "rule": ctl_rule, "soft": ctl_soft, "shield": ctl_shield,
               "medical_only": ctl_medical_only}


def shield_reserve(b, name, hours, pv, t, p90_end):
    horizon = max(12, p90_end - t)
    need = 0.0
    for k in range(1, horizon + 1):
        h = hours[(t + k) % len(hours)]
        pv_f = 0.7 * pv[t + k - 24] if 0 <= t + k - 24 < len(pv) else 0.0
        need += max(0.0, crit_kw(name, h) - pv_f)
    return need


# ------------------------------------------------------------------ episode
def run_episode(controller, day, duration, precharge=False, w_heat=1.0, batt_kwh=13.5, hour=14, p90=P90_H):
    start = JUL1 + (day - 1) * 24 + hour
    env, outage = make_env(start, duration, batt_kwh=batt_kwh, batt_kw=batt_kwh * 5.0 / 13.5)
    env.reset()
    blds = env.buildings
    hours = [[(h - 1) % 24 for h in b.energy_simulation.hour] for b in blds]
    pv = [np.asarray(b.pv.get_generation(b.energy_simulation.solar_generation)) for b in blds]
    plan = {b.name: {} for b in blds}
    ctrl = CONTROLLERS[controller]
    while not env.terminated:
        t = env.time_step
        acts = []
        for i, b in enumerate(blds):
            bs, es = b.electrical_storage, b.energy_simulation
            nom = bs.nominal_power
            cool_req = thermostat_kw(b, t)
            if t < len(outage) and outage[t]:
                avail, soc = batt_avail_kwh(b, t)
                batt_kw_avail = min(nom * 0.97, avail)
                hr = hours[i][t]
                devs = devices_at(b.name, hr)
                tin = es.indoor_dry_bulb_temperature[t - 1]
                c = {"t": t, "pv": float(pv[i][t]), "soc": soc, "batt_kwh": avail, "batt_kw": nom,
                     "batt_kw_avail": batt_kw_avail, "supply": float(pv[i][t]) + batt_kw_avail,
                     "devices": devs, "ess": ESSENTIAL_KW, "cool": cool_req, "w_heat": w_heat,
                     "risk": max(0.0, tin - CAUTION_C) / (DANGER_C - CAUTION_C) * MED[b.name]["residents"],
                     "forecast_end": WARM + FORECAST_H, "reserve": 0.0}
                if controller == "shield":
                    c["reserve"] = shield_reserve(b, b.name, hours[i], pv[i], t, WARM + p90)
                on, ess, cool = ctrl(c)
                served = sum(kw for kw, ok in zip(devs, on) if ok) + ess + cool
                net = served - c["pv"]
                a_batt = -min(1.0, net / nom) if net > 0 else min(1.0, -net / nom)
                plan[b.name][t] = {"devices": devs, "on": on, "ess_shed": ESSENTIAL_KW - ess,
                                   "crit_shed": sum(kw for kw, ok in zip(devs, on) if not ok)}
            else:
                cool = cool_req
                load = es.non_shiftable_load[t] + cool - pv[i][t]
                soc = bs.soc[t - 1] if t > 0 else bs.initial_soc
                pre = precharge and t >= WARM - 24 and t < WARM
                if pre:
                    a_batt = min(1.0, max(0.0, (1 - soc) * bs.capacity) / nom)
                elif load < 0:
                    a_batt = min(1.0, -load / nom)
                else:
                    a_batt = -min(1.0, load / nom, max(0.0, soc - RESERVE_GRID) * bs.capacity * 0.9 / nom)
            a_cool = -min(1.0, cool / b.cooling_device.nominal_power) if b.cooling_device.nominal_power > 0 else 0.0
            for an in b.active_actions:
                acts.append(a_cool if an == "cooling_or_heating_device" else a_batt if an == "electrical_storage" else 0.0)
        env.step([acts])

    # metrics over the outage hours
    m = {"crit_device_hours_down": 0, "crit_kwh_unserved": 0.0, "crit_kwh_demand": 0.0,
         "person_hours_danger": 0.0, "person_degree_hours": 0.0, "max_tin": 0.0,
         "unserved_kwh": 0.0, "infeasible_kwh": 0.0, "soc0": 0.0, "essential_kwh_unserved": 0.0}
    for b in blds:
        res = MED[b.name]["residents"]
        tin = np.asarray(b.indoor_dry_bulb_temperature)
        net = np.asarray(b.net_electricity_consumption)
        m["soc0"] += b.electrical_storage.soc[WARM - 1] / len(blds)
        for t in range(WARM, WARM + duration):
            p = plan[b.name][t]
            # grid import CityLearn recorded beyond what the controller chose to shed means the
            # plan was infeasible for the battery model; count it against medical devices first
            extra = max(0.0, net[t] - p["crit_shed"] - p["ess_shed"] - 1e-3)
            m["infeasible_kwh"] += extra
            down = [not ok for ok in p["on"]]
            for j, kw in enumerate(p["devices"]):
                if not down[j] and extra > 1e-3:
                    down[j], extra = True, max(0.0, extra - kw)
            m["crit_device_hours_down"] += sum(down)
            m["crit_kwh_unserved"] += sum(kw for kw, d in zip(p["devices"], down) if d)
            m["crit_kwh_demand"] += sum(p["devices"])
            m["unserved_kwh"] += max(0.0, net[t])
            m["essential_kwh_unserved"] += p["ess_shed"]
            m["person_hours_danger"] += res * (tin[t] > DANGER_C)
            m["person_degree_hours"] += res * max(0.0, tin[t] - CAUTION_C)
            m["max_tin"] = max(m["max_tin"], float(tin[t]))
    d = m["crit_kwh_demand"]
    m["crit_served_pct"] = 100.0 * (1 - m["crit_kwh_unserved"] / d) if d else 100.0
    return {"controller": controller, "day": day, "duration_h": duration, "precharge": precharge,
            "w_heat": w_heat, "batt_kwh": batt_kwh, "start_hour": hour, "p90_h": p90, **m}


def _job(args):
    exp, kw = args
    return {"experiment": exp, **run_episode(**kw)}


def jobs(quick=False):
    days = [19] if quick else range(1, 29)
    durs = [48] if quick else [12, 24, 48, 72]
    out = []
    for c, d, dur, pre in itertools.product(CONTROLLERS, days, durs, [False, True]):
        out.append(("main", dict(controller=c, day=d, duration=dur, precharge=pre)))
    if not quick:
        for c, d, w in itertools.product(["soft", "shield"], days, [0.25, 0.5, 1, 2, 4, 8]):
            out.append(("w_heat", dict(controller=c, day=d, duration=48, w_heat=w)))
        for c, d, bk in itertools.product(CONTROLLERS, days, [6.75, 13.5, 27.0, 40.5]):
            out.append(("battery", dict(controller=c, day=d, duration=48, batt_kwh=bk)))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    js = jobs(args.quick)
    t0 = time.time()
    print(f"{len(js)} CityLearn episodes")
    with Pool() as pool:
        rows = pool.map(_job, js, chunksize=4)
    df = pd.DataFrame(rows)
    name = "scenarios_quick.csv" if args.quick else "scenarios.csv"
    df.to_csv(OUT / name, index=False)
    print(f"done in {time.time() - t0:.0f}s -> {OUT / name}")
    if args.quick:
        cols = ["controller", "precharge", "crit_device_hours_down", "crit_served_pct", "person_hours_danger",
                "person_degree_hours", "essential_kwh_unserved", "max_tin", "soc0", "infeasible_kwh"]
        print(df[cols].round(2).to_string(index=False))
