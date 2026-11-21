"""Regenerate every CareGrid result from scratch, in dependency order.

    python run_all.py                 # everything (about 2-3 hours on 8 CPU cores)
    python run_all.py --skip-long     # skip RL training and the CityLearn grids
    python run_all.py --only forecast ablations

Main environment: .venv (requirements.txt). CityLearn stages use .venv-citylearn
(requirements-citylearn.txt); set CITYLEARN_PYTHON to use another interpreter.
"""
import argparse
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
PY = sys.executable
CL = os.environ.get("CITYLEARN_PYTHON", str(ROOT / ".venv-citylearn" / "bin" / "python"))

# (name, interpreter, command, long?) in dependency order
STAGES = [
    ("inputs",      PY, ["data/fetch_data.py"], False),
    ("eaglei",      "zsh", ["personC/forecast/fetch_eaglei.sh"], False),
    ("parity",      PY, ["tests/test_parity.py"], False),
    ("main_grid",   PY, ["experiments/run_pilot.py"], True),
    ("main_tables", PY, ["experiments/analyze.py"], False),
    ("personA",     PY, ["experiments/robustness.py", "experiments/robustness_battery.py",
                         "experiments/robustness_sensor.py", "experiments/personA_graphs.py"], False),
    ("baselines",   PY, ["personC/step2/check_baselines.py"], False),
    ("health_twin", PY, ["personC/step3/ablation.py"], False),
    ("forecast",    PY, ["personC/forecast/outage_forecast.py"], False),
    ("phoenix_rl",  PY, ["personC/phoenix_rl/train.py"], True),
    ("phoenix_rl_report", PY, ["personC/phoenix_rl/report.py"], False),
    ("citylearn",   CL, ["citylearn_port/run_citylearn.py", "citylearn_port/analyze_citylearn.py"], True),
    ("mappo",       CL, ["personC/citylearn_rl/mappo.py"], True),
    ("mappo_report", PY, ["personC/citylearn_rl/report.py"], False),
    ("ablations",   PY, ["personC/step7/ablations.py"], False),
    ("robustness",  PY, ["personC/step7/robustness.py"], False),
    ("paper",       PY, ["paper_team/make_paper.py"], False),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-long", action="store_true", help="skip RL training and the large simulation grids")
    ap.add_argument("--only", nargs="*", help="run only these stages")
    args = ap.parse_args()
    names = [s[0] for s in STAGES]
    for n in args.only or []:
        if n not in names:
            sys.exit(f"unknown stage {n!r}; stages: {', '.join(names)}")
    t_all = time.time()
    for name, interp, scripts, long in STAGES:
        if args.only and name not in args.only:
            continue
        if args.skip_long and long and not args.only:
            print(f"-- {name}: skipped (--skip-long)")
            continue
        for script in scripts:
            t = time.time()
            print(f"-- {name}: {script}", flush=True)
            r = subprocess.run([interp, str(ROOT / script)], cwd=ROOT)
            if r.returncode != 0:
                sys.exit(f"stage {name} failed in {script} (exit {r.returncode})")
            print(f"   done in {(time.time() - t) / 60:.1f} min", flush=True)
    print(f"all stages done in {(time.time() - t_all) / 60:.1f} min")


if __name__ == "__main__":
    main()
