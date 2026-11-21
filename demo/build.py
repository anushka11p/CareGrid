"""Inline the engine, the real weather/load data and the pilot summary into demo/caregrid_demo.html."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
d = json.loads((ROOT / "data" / "processed" / "phoenix_july2023.json").read_text())
w = d["weather"]
data = {"time": w["time"], "hour": [int(t[11:13]) for t in w["time"]], "temp": w["temp_c"],
        "ghi": w["ghi_wm2"], "poa": w["poa_wm2"], "baseKw": d["resstock"]["base_kw_by_hour"]}
summary_path = ROOT / "results" / "summary.json"
s = json.loads(summary_path.read_text()) if summary_path.exists() else None
pilot = None
if s:
    pool = s["pooled"]["False"]
    bd = s["by_duration_crit"]
    tests = {(t["a"], t["b"], t["metric"]): t for t in s["tests"]}
    heat = tests[("soft", "shield", "person_degree_hours")]
    pilot = {
        "by_duration_crit": bd,
        "findings": [
            {"big": f"{pool['shield']['crit_device_hours_down']:.1f} vs {pool['soft']['crit_device_hours_down']:.1f}",
             "col": "--accent", "title": "Medical device-hours lost per outage, shield vs weighted",
             "text": f"Pooled over 112 outages with no warning. The weighted controller kept "
                     f"{pool['soft']['crit_served_pct']:.1f}% of critical energy flowing; the shield kept "
                     f"{pool['shield']['crit_served_pct']:.1f}%."},
            {"big": f"{s['w_heat']['mpc']['2.0'][0]:.0f} h", "col": "--soft",
             "title": "Double the heat weight and the planner drops medical loads",
             "text": f"A planning controller (MPC) with a perfect weather forecast is nearly safe at its default weights "
                     f"({s['w_heat']['mpc']['1.0'][0]:.1f} device-hours lost per 48 h outage). At twice the weight on cooling it loses "
                     f"{s['w_heat']['mpc']['2.0'][0]:.0f}. The shielded planner loses 0 at every weight tested."},
            {"big": f"+{100 * (heat['mean_b'] / heat['mean_a'] - 1):.0f}%", "col": "--ink",
             "title": "Price of the guarantee: more heat exposure",
             "text": f"The shield's reserve raises resident heat exposure (person-degree-hours above 26.7 °C) from "
                     f"{heat['mean_a']:.0f} to {heat['mean_b']:.0f} per outage. The perfect-foresight bound shows room to close that gap."},
        ],
    }
    cl_path = ROOT / "results" / "citylearn" / "summary.json"
    if cl_path.exists():
        cl = json.loads(cl_path.read_text())
        t = cl["tests"]["crit_device_hours_down"]
        pilot["findings"].append({
            "big": f"{t['shield']:.1f} vs {t['soft']:.1f}", "col": "--accent",
            "title": "Replicated on CityLearn v3 (Austin, TX)",
            "text": f"Same controllers on CityLearn's ResStock homes with LSTM indoor temperatures and 2018 Austin weather: "
                    f"medical device-hours lost per outage, shield vs weighted ({100 * (1 - t['shield'] / t['soft']):.0f}% fewer, "
                    f"p = {t['p']:.1g}). Heat exposure rose from {cl['tests']['person_hours_danger']['soft']:.0f} to "
                    f"{cl['tests']['person_hours_danger']['shield']:.0f} person-hours above 32.2 °C."})
html = (ROOT / "demo" / "template.html").read_text()
html = html.replace("/*__ENGINE__*/", (ROOT / "demo" / "engine.js").read_text())
html = html.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
html = html.replace("/*__SUMMARY__*/null", json.dumps(pilot, separators=(",", ":")))
out = ROOT / "demo" / "caregrid_demo.html"
out.write_text(html)
print("wrote", out, f"{len(html) / 1024:.0f} KB", "with pilot results" if pilot else "WITHOUT pilot results")
