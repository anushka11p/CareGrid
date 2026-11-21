"""Build the CareGrid CityLearn dataset from CityLearn's own `tx_travis_county_neighborhood`.

Source: 100 NREL ResStock (2021 release, AMY2018) homes in Travis County (Austin), TX, with
measured 2018 weather (Camp Mabry station) and per-home LSTM indoor-temperature models,
shipped with CityLearn v3.

Changes for CareGrid (applied identically for every controller):
  * keep the first 10 homes in schema order that have summer cooling
  * fixed assets per home: 6 kW rooftop PV, 13.5 kWh / 5 kW home battery
  * PV output per kW computed with NREL PVWatts v8 (PySAM) from the dataset's own EPW file
  * each home's elderly residents and medical devices (critical loads) are listed in
    medical.json; their power is added to the home's non-shiftable load
Writes data/citylearn/caregrid_travis/.
"""
import json
import pathlib
import shutil

import numpy as np
import pandas as pd
import PySAM.Pvwattsv8 as pvwatts
from citylearn.data import DataSet

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "citylearn" / "caregrid_travis"
N_HOMES = 10
PV_KW, BATT_KWH, BATT_KW = 6.0, 13.5, 5.0
NIGHT = [22, 23, 0, 1, 2, 3, 4, 5]
O2 = ("oxygen concentrator", 0.35, [])
# (residents, devices) for each home, mirroring the Phoenix pilot's households
HOUSEHOLDS = [
    (1, [O2]),
    (2, [("CPAP", 0.06, NIGHT), ("insulin fridge", 0.12, [])]),
    (1, [O2]),
    (1, []),
    (2, [("power wheelchair charger", 0.30, [22, 23, 0, 1])]),
    (1, [("CPAP", 0.06, NIGHT), ("insulin fridge", 0.12, [])]),
    (1, [O2]),
    (2, []),
    (2, [O2, ("medication fridge", 0.15, [])]),
    (1, [("home ventilator", 0.15, []), ("CPAP", 0.06, NIGHT)]),
]


def pv_per_kw(epw):
    m = pvwatts.default("PVWattsNone")
    m.SolarResource.solar_resource_file = str(epw)
    m.SystemDesign.system_capacity = 1.0
    m.SystemDesign.tilt = 20.0
    m.SystemDesign.azimuth = 180.0
    m.execute()
    return np.array(m.Outputs.ac, dtype=float)  # W per kW, hourly, 8760


def device_kw_by_hour(devices):
    return [sum(kw for _, kw, hours in devices if not hours or h in hours) for h in range(24)]


def main():
    src_schema = pathlib.Path(DataSet().get_dataset("tx_travis_county_neighborhood"))
    src = src_schema.parent
    s = json.loads(src_schema.read_text())
    OUT.mkdir(parents=True, exist_ok=True)

    pv = pv_per_kw(src / "weather.epw")
    chosen = []
    for name, b in s["buildings"].items():
        df = pd.read_csv(src / b["energy_simulation"])
        summer = df[df.month.isin([7, 8])]
        if summer.cooling_demand.sum() > 0:
            chosen.append(name)
        if len(chosen) == N_HOMES:
            break

    medical = {}
    buildings = {}
    for i, name in enumerate(chosen):
        b = s["buildings"][name]
        df = pd.read_csv(src / b["energy_simulation"])
        residents, devices = HOUSEHOLDS[i]
        crit = device_kw_by_hour(devices)
        # CSV hour column is 1..24 (hour ending); hour-of-day h covers [h-1, h)
        hod = (df.hour - 1) % 24
        df["non_shiftable_load"] = df.non_shiftable_load + hod.map(lambda h: crit[h])
        df["solar_generation"] = pv[: len(df)]
        short = f"home_{i + 1:02d}"
        df.to_csv(OUT / f"{short}.csv", index=False)
        shutil.copy(src / b["dynamics"]["attributes"]["filename"], OUT / f"{short}.pth")
        b = json.loads(json.dumps(b))
        b["include"] = True
        b["energy_simulation"] = f"{short}.csv"
        b["dynamics"]["attributes"]["filename"] = f"{short}.pth"
        b["pv"] = {"type": "citylearn.energy_model.PV", "autosize": False, "attributes": {"nominal_power": PV_KW}}
        b["electrical_storage"] = {"type": "citylearn.energy_model.Battery", "autosize": False,
                                   "attributes": {"capacity": BATT_KWH, "nominal_power": BATT_KW, "efficiency": 0.95,
                                                  "initial_soc": 0.5}}
        b["power_outage"] = {"simulate_power_outage": True, "stochastic_power_outage": False}
        buildings[short] = b
        medical[short] = {"resstock_id": name, "residents": residents,
                          "devices": [{"name": n, "kw": kw, "hours": h} for n, kw, h in devices],
                          "critical_kw_by_hour": crit}

    for f in ("weather.csv", "weather.epw"):
        shutil.copy(src / f, OUT / f)
    for f in ("carbon_intensity.csv", "pricing.csv"):
        if (src / f).exists():
            shutil.copy(src / f, OUT / f)
    s["buildings"] = buildings
    s["root_directory"] = None
    s["actions"]["dhw_storage"]["active"] = False
    (OUT / "schema.json").write_text(json.dumps(s, indent=1))
    (OUT / "medical.json").write_text(json.dumps(medical, indent=1))
    print(f"wrote {OUT} with {len(buildings)} homes; PV {pv.sum() / 1000:.0f} kWh/kW-yr")
    for k, v in medical.items():
        print(k, v["resstock_id"], v["residents"], [d["name"] for d in v["devices"]])


if __name__ == "__main__":
    main()
