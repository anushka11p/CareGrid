"""The browser demo (demo/engine.js) must reproduce the Python simulator exactly.
Run: python3 tests/test_parity.py   (needs Node.js)"""
import itertools
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from caregrid.sim import Assets, community, load_inputs, metrics, run_normal, run_outage  # noqa: E402

KEYS = ["crit_device_hours_down", "crit_kwh_unserved", "person_hours_danger",
        "person_degree_hours", "hw_ens", "max_tin", "pv_curtailed_kwh"]


def python_case(inp, ctrl, day, dur, pre, batt, w):
    a = Assets(batt_kwh=batt, batt_kw=batt * 0.4)
    blds = community()
    start = 24 * day + 14
    states, _ = run_normal(inp, a, blds)
    if pre:
        soc, tin = states[start - 24]
        st, _ = run_normal(inp, a, blds, t0=start - 24, t1=start, soc0=soc, tin0=tin, precharge_from=start - 24)
        soc0, tin0 = st[start]
    else:
        soc0, tin0 = states[start]
    return metrics(run_outage(inp, a, blds, start, dur, ctrl, soc0, tin0, w_heat=w), blds)


def main():
    inp = load_inputs()
    cases = list(itertools.product(["equal", "rule", "soft", "shield"], [3, 19], [24, 72], [False, True],
                                   [100.0, 250.0], [1.0, 4.0]))
    js_inp = {"time": inp["time"], "hour": inp["hour"], "temp": inp["temp"], "ghi": inp["ghi"],
              "poa": inp["poa"], "baseKw": inp["base_kw"]}
    script = """
const E = require(%s); const inp = %s; const cases = %s;
console.log(JSON.stringify(cases.map(([c, day, dur, pre, batt, w]) =>
  E.scenario(inp, {controller: c, day, duration: dur, precharge: pre, wHeat: w,
                   assets: {battKwh: batt, battKw: batt * 0.4}}).metrics)));
""" % (json.dumps(str(ROOT / "demo" / "engine.js")), json.dumps(js_inp), json.dumps(cases))
    script_path = ROOT / "tests" / "parity_temp.js"
    script_path.write_text(script, encoding="utf-8")
    try:
        result = subprocess.run(
            ["node", str(script_path)],
            capture_output=True,
            text=True,
            check=True,
            cwd=ROOT
        )
        js = json.loads(result.stdout)
    finally:
        script_path.unlink(missing_ok=True)
    worst = 0.0
    for case, jm in zip(cases, js):
        pm = python_case(inp, *case)
        for k in KEYS:
            diff = abs(pm[k] - jm[k])
            worst = max(worst, diff)
            assert diff < 1e-6, f"{case} {k}: python {pm[k]} vs js {jm[k]}"
    print(f"parity OK on {len(cases)} scenarios (max abs diff {worst:.2e})")


if __name__ == "__main__":
    main()
