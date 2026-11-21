"""Step 2: run every baseline and check that they behave as their definitions say.

Writes personC/step2/case_study.csv (19 July 14:00, 48 h), personC/step2/all_runs.csv
(28 start days x 48/72 h, no warning) and prints the sanity checks."""
import itertools
import pathlib
import sys
from multiprocessing import Pool

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from caregrid.oracle import run_oracle  # noqa: E402
from caregrid.sim import Assets, community, load_inputs, metrics, run_normal, run_outage  # noqa: E402

CTRLS = ["equal", "rule", "soft", "shield", "mpc", "mpc_hi", "mpc_p90", "mpc_shield", "mpc_p90_shield", "oracle"]
INP, A, BLDS = load_inputs(), Assets(), community()
STATES, _ = run_normal(INP, A, BLDS)


def run(job):
    ctrl, day, dur = job
    start = 24 * day + 14
    soc0, tin0 = STATES[start]
    if ctrl == "oracle":
        m = run_oracle(INP, A, BLDS, start, dur, soc0, tin0)
    else:
        m = metrics(run_outage(INP, A, BLDS, start, dur, ctrl, soc0, tin0), BLDS)
    return {"controller": ctrl, "day": day, "duration_h": dur, **m}


if __name__ == "__main__":
    out = ROOT / "personC" / "step2"
    with Pool(6) as p:
        case = pd.DataFrame(p.map(run, [(c, 19, 48) for c in CTRLS]))
        allr = pd.DataFrame(p.map(run, list(itertools.product(CTRLS, range(1, 29), (48, 72))), chunksize=4))
    cols = ["controller", "crit_device_hours_down", "crit_served_pct", "person_hours_danger", "person_degree_hours", "max_tin"]
    case[cols].round(1).to_csv(out / "case_study.csv", index=False)
    allr.to_csv(out / "all_runs.csv", index=False)
    print("Case study, 19 July 14:00, 48 h\n" + case[cols].round(1).to_string(index=False))

    piv = allr.pivot_table(index=["day", "duration_h"], columns="controller", values="crit_device_hours_down")
    pdh = allr.pivot_table(index=["day", "duration_h"], columns="controller", values="person_degree_hours")
    checks = []
    others = [c for c in CTRLS if c != "oracle"]
    checks.append(("Oracle loses no more medical service than any controller, every outage",
                   bool((piv[others].ge(piv["oracle"], axis=0)).all().all())))
    # The bound minimises heat plus 2 x essential energy unserved (and 0.01 x discretionary),
    # after medical service; compare controllers on that same score.
    allr["objective"] = allr.person_degree_hours + 2.0 * allr.ess_kwh_unserved
    obj = allr.pivot_table(index=["day", "duration_h"], columns="controller", values="objective")
    safe = piv[others] <= 1e-9
    worse = [(obj[c][safe[c]] >= obj["oracle"][safe[c]] - 1e-3).all() for c in others]
    checks.append(("Oracle has the best heat + essential-load score among controllers that keep every device powered",
                   bool(all(worse))))
    checks.append(("MPC planned to P90 loses no more medical service than MPC planned to the estimate (mean)",
                   bool(piv["mpc_p90"].mean() <= piv["mpc"].mean())))
    checks.append(("Equal curtailment has the most medical device-hours lost (mean)",
                   piv.mean().idxmax() == "equal"))
    checks.append(("Every shielded controller loses at most 0.5 device-hours per outage (mean)",
                   bool(piv[["shield", "mpc_shield", "mpc_p90_shield"]].mean().max() <= 0.5)))
    print("\nSanity checks over 28 days x 48/72 h:")
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print("\nMean device-hours lost:\n" + piv.mean().round(1).to_string())
    pd.DataFrame(checks, columns=["check", "passed"]).to_csv(out / "checks.csv", index=False)
