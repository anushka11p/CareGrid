"""Probe CityLearn behaviour during an outage: battery-backed cooling and LSTM temperatures."""
import json
import pathlib

import numpy as np
from citylearn.citylearn import CityLearnEnv

DS = pathlib.Path(__file__).resolve().parent.parent / "data" / "citylearn" / "caregrid_travis"
JUL1 = 181 * 24
START = JUL1 + 18 * 24 + 14          # 19 July 2018, 14:00 (index of the hour starting 14:00)
WARM, DUR = 48, 48


def make_env():
    s = json.loads((DS / "schema.json").read_text())
    s["root_directory"] = str(DS)
    s["simulation_start_time_step"] = START - WARM
    s["simulation_end_time_step"] = START + DUR + 2
    s["central_agent"] = True
    env = CityLearnEnv(s)
    for b in env.buildings:
        sig = np.zeros(len(b.energy_simulation.power_outage))
        sig[WARM:WARM + DUR] = 1
        b.energy_simulation.power_outage[:] = sig
    return env


def run(cool_mode):
    env = make_env()
    env.reset()
    rows = []
    while not env.terminated:
        t = env.time_step
        acts = []
        for b in env.buildings:
            nxt = t + 1
            demand = b.energy_simulation.cooling_demand_without_control[nxt]
            temp = b.weather.outdoor_dry_bulb_temperature[nxt]
            cop = b.cooling_device.get_cop(temp, heating=False)
            a_cool = min(1.0, demand / cop / b.cooling_device.nominal_power)
            outage_next = b.energy_simulation.power_outage[nxt] > 0
            if cool_mode == "off" and outage_next:
                a_cool = 0.0
            # battery: discharge flat out during the outage (CityLearn caps it at local load)
            a_batt = -1.0 if outage_next else 0.0
            for an in b.active_actions:
                acts.append(-a_cool if an == "cooling_or_heating_device" else a_batt if an == "electrical_storage" else 0.0)
        env.step([acts])
        b = env.buildings[0]
        k = env.time_step
        if env.terminated:
            break
        rows.append((k - WARM, b.weather.outdoor_dry_bulb_temperature[k], b.indoor_dry_bulb_temperature[-1],
                     b.electrical_storage.soc[-1], b.non_shiftable_load[-1], b.non_shiftable_load_electricity_consumption[-1],
                     b.cooling_electricity_consumption[-1], -b.solar_generation[-1], b.power_outage_signal[-1]))
    return rows


if __name__ == "__main__":
    env = make_env()
    b = env.buildings[0]
    print("episode arrays length", len(b.energy_simulation.power_outage), "cool kW", round(b.cooling_device.nominal_power, 2))
    for mode in ("on", "off"):
        print(f"\n=== cooling {mode} during outage (home_01) ===")
        print("  h   out   Tin   soc  nsl_dem nsl_srv cool_el  pv  out?")
        for r in run(mode):
            if -4 <= r[0] <= DUR + 1 and r[0] % 3 == 0:
                print(f"{r[0]:4d} {r[1]:5.1f} {r[2]:5.1f} {r[3]:5.2f} {r[4]:6.2f} {r[5]:6.2f} {r[6]:6.2f} {r[7]:5.2f} {int(r[8])}")
