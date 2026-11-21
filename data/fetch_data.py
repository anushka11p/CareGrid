"""Download and preprocess the real inputs used by the CareGrid pilot.

Sources (all public, no key needed):
  * Open-Meteo historical archive (ERA5-based reanalysis): hourly air temperature,
    relative humidity, global horizontal and plane-of-array irradiance for Phoenix, AZ.
  * NREL ResStock 2021 release (AMY2018), county aggregate for Maricopa County, AZ,
    single-family detached: used for the non-cooling household load shape and to
    calibrate cooling energy.

Writes data/processed/phoenix_july2023.json, which every other script reads.
"""
import json
import pathlib
import subprocess

import pandas as pd

import math


def validate_data(data):
    """Validate acquired weather and household-load data before saving."""
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary.")

    weather = data.get("weather")
    if not isinstance(weather, dict):
        raise ValueError("Missing or invalid weather data.")

    required = {
        "time": 840,
        "temp_c": 840,
        "rh_pct": 840,
        "ghi_wm2": 840,
        "poa_wm2": 840,
    }

    for name, expected_length in required.items():
        values = weather.get(name)
        if not isinstance(values, list):
            raise ValueError(f"Weather field '{name}' must be a list.")
        if len(values) != expected_length:
            raise ValueError(
                f"Weather field '{name}' has {len(values)} values; "
                f"expected {expected_length}."
            )

    if len(set(weather["time"])) != len(weather["time"]):
        raise ValueError("Weather timestamps contain duplicates.")

    for name in ("temp_c", "rh_pct", "ghi_wm2", "poa_wm2"):
        values = weather[name]
        if any(
            not isinstance(v, (int, float))
            or isinstance(v, bool)
            or not math.isfinite(v)
            for v in values
        ):
            raise ValueError(f"Weather field '{name}' has invalid values.")

    if any(not 0 <= v <= 100 for v in weather["rh_pct"]):
        raise ValueError("Humidity must be between 0 and 100 percent.")

    if any(v < 0 for name in ("ghi_wm2", "poa_wm2")
           for v in weather[name]):
        raise ValueError("Solar radiation cannot be negative.")

    loads = data.get("resstock", {}).get("base_kw_by_hour")
    if not isinstance(loads, list) or len(loads) != 24:
        raise ValueError("Household load profile must contain 24 hourly values.")

    if any(
        not isinstance(v, (int, float))
        or isinstance(v, bool)
        or not math.isfinite(v)
        or v < 0
        for v in loads
    ):
        raise ValueError("Household load profile contains invalid values.")

    print("Data validation passed.")


ROOT = pathlib.Path(__file__).resolve().parent
RAW = ROOT / "raw"
OUT = ROOT / "processed"
RAW.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

LAT, LON = 33.4484, -112.0740  # Phoenix, AZ
START, END = "2023-06-30", "2023-08-03"
WEATHER_URL = (
    "https://archive-api.open-meteo.com/v1/archive"
    f"?latitude={LAT}&longitude={LON}&start_date={START}&end_date={END}"
    "&hourly=temperature_2m,relative_humidity_2m,shortwave_radiation,global_tilted_irradiance"
    "&tilt=25&azimuth=0&timezone=America%2FPhoenix"
)
RESSTOCK_URL = (
    "https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/"
    "end-use-load-profiles-for-us-building-stock/2021/resstock_amy2018_release_1/"
    "timeseries_aggregates/by_county/state=AZ/g0400130-single-family_detached.csv"
)


def fetch(url, path):
    if not path.exists():
        print("downloading", url)
        # curl uses the system trust store; some Python builds ship without CA certs.
        subprocess.run(["curl", "-sSfL", "-o", str(path), url], check=True)
    return path


def weather():
    raw = json.loads(fetch(WEATHER_URL, RAW / "openmeteo_phoenix_2023.json").read_text())
    h = raw["hourly"]
    return {
        "time": h["time"],
        "temp_c": h["temperature_2m"],
        "rh_pct": h["relative_humidity_2m"],
        "ghi_wm2": h["shortwave_radiation"],
        "poa_wm2": h["global_tilted_irradiance"],
    }


def resstock():
    d = pd.read_csv(fetch(RESSTOCK_URL, RAW / "maricopa_sfd.csv"), parse_dates=["timestamp"])
    units = d["units_represented"].iloc[0]
    d = d.set_index("timestamp")
    # ResStock timestamps mark the END of each 15-min interval; shift to interval start.
    d.index = d.index - pd.Timedelta(minutes=15)
    jul = d["2018-07-01":"2018-07-31 23:59"]

    def col(name):
        return jul[f"out.electricity.{name}.energy_consumption"] / units  # kWh per home per 15 min

    cooling = col("cooling") + col("fans_cooling")
    non_base = ["cooling", "fans_cooling", "pool_pump", "pool_heater", "vehicle", "pv",
                "hot_tub_heater", "hot_tub_pump"]
    base = col("total") - sum(col(n) for n in non_base)
    base_kw_by_hour = (base * 4).groupby(base.index.hour).mean()
    return {
        "units_represented": float(units),
        "base_kw_by_hour": [round(v, 4) for v in base_kw_by_hour.tolist()],
        "july2018_cooling_kwh_per_day": round(float(cooling.resample("D").sum().mean()), 2),
        "july2018_total_kwh_per_day": round(float(col("total").resample("D").sum().mean()), 2),
    }


if __name__ == "__main__":
    out = {
        "location": {"name": "Phoenix, AZ", "lat": LAT, "lon": LON},
        "sources": {"weather": WEATHER_URL, "loads": RESSTOCK_URL},
        "weather": weather(),
        "resstock": resstock(),
    }
    validate_data(out)
    (OUT / "phoenix_july2023.json").write_text(json.dumps(out))
    w = out["weather"]
    print("hours:", len(w["time"]), w["time"][0], "->", w["time"][-1])
    print("max temp:", max(w["temp_c"]), "C")
    print("resstock:", {k: v for k, v in out["resstock"].items() if k != "base_kw_by_hour"})
