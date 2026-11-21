"""Step 7: ablations. Each row changes one element and compares paired outages.

Sources: Step 3 (shield cooling order), Step 5 Phoenix RL (5 seeds per configuration; learned
results are averaged over seeds per outage before pairing), Step 4 forecaster (shield re-run
here with the forecast worst-case and median restoration times).
Statistics: mean of each arm, mean paired difference with a 95 % bootstrap interval
(10,000 resamples of outages), and a paired Wilcoxon signed-rank test.
Writes personC/step7/ablations.csv, forecast_runs.csv and results.md.
"""
import itertools
import json
import math
import pathlib
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = pathlib.Path(__file__).resolve().parent
KEYS = ["day", "duration_h"]
METRICS = {"crit_device_hours_down": "Medical device-hours lost", "vuln_degree_hours": "Vulnerability-weighted degree-h",
           "person_hours_danger": "Person-hours > 32.2 C"}


def paired(name, a_label, b_label, a, b, n_seeds=None):
    a, b = a.sort_index(), b.sort_index()
    b = b.loc[a.index]
    rng = np.random.default_rng(0)
    rows = []
    for k, label in METRICS.items():
        d = (b[k] - a[k]).to_numpy()
        boots = rng.choice(d, (10000, len(d))).mean(1)
        lo, hi = np.percentile(boots, [2.5, 97.5])
        p = wilcoxon(a[k], b[k]).pvalue if np.any(d != 0) else 1.0
        rows.append({"ablation": name, "A": a_label, "B": b_label, "metric": label, "n_outages": len(d),
                     "seeds": n_seeds or 1, "mean_A": a[k].mean(), "mean_B": b[k].mean(), "diff_B_minus_A": d.mean(),
                     "ci_low": lo, "ci_high": hi, "p": p})
    return rows


def seed_mean(df, controller):
    g = df[df.controller == controller]
    return g.groupby(KEYS)[list(METRICS)].mean(), g.seed.nunique()


def forecast_run(job):
    from caregrid.sim import Assets, community, load_inputs, metrics, run_normal, run_outage
    label, p90, est, warning, day, dur = job
    inp, a, blds = load_inputs(), Assets(), community()
    states, _ = run_normal(inp, a, blds)
    start = 24 * day + 14
    if warning:
        soc, tin = states[start - 24]
        st, _ = run_normal(inp, a, blds, t0=start - 24, t1=start, soc0=soc, tin0=tin, precharge_from=start - 24)
        soc0, tin0 = st[start]
    else:
        soc0, tin0 = states[start]
    m = metrics(run_outage(inp, a, blds, start, dur, "shield", soc0, tin0, forecast_hours=est, p90_hours=p90), blds)
    return {"setting": label, "p90_h": p90, "estimate_h": est, "warning": warning, "day": day, "duration_h": dur, **m}


def main():
    rows = []
    # 1. shield vs no shield
    base = pd.read_csv(ROOT / "personC" / "phoenix_rl" / "results" / "baselines.csv")
    rl = pd.read_csv(ROOT / "personC" / "phoenix_rl" / "results" / "eval.csv")
    for w in (False, True):
        bw = base[base.warning == w]
        soft = bw[bw.controller == "soft"].set_index(KEYS)[list(METRICS)]
        shield = bw[bw.controller == "shield"].set_index(KEYS)[list(METRICS)]
        tag = "warning" if w else "no warning"
        rows += paired(f"Shield ({tag}, greedy)", "priority as weight", "shield", soft, shield)
        on, n1 = seed_mean(rl, "warn" if w else "nowarn")
        off, n2 = seed_mean(rl, "warn_noshield" if w else "nowarn_noshield")
        rows += paired(f"Shield ({tag}, learned policy)", "PPO-Lag. without reserve", "PPO-Lag. inside shield", off, on, n1)
    # 2. health twin vs headcount
    s3 = pd.read_csv(ROOT / "personC" / "step3" / "ablation.csv")
    rows += paired("Health twin (shield cooling order)", "building order", "health-twin order",
                   s3[s3.order == "index"].set_index(KEYS)[list(METRICS)],
                   s3[s3.order == "health_twin"].set_index(KEYS)[list(METRICS)])
    uni, n = seed_mean(rl, "warn_uniform")
    twin, _ = seed_mean(rl, "warn")
    rows += paired("Health twin (learned-policy reward, warning)", "headcount reward", "health-twin reward", uni, twin, n)
    # 3. learned policy vs fixed pacing, both inside the shield
    for w in (False, True):
        bw = base[base.warning == w]
        fixed = bw[bw.controller == "shield"].set_index(KEYS)[list(METRICS)]
        learned, n = seed_mean(rl, "warn" if w else "nowarn")
        rows += paired(f"Learned release ({'warning' if w else 'no warning'})", "fixed pacing", "PPO-Lag.", fixed, learned, n)
    # 4. forecast worst case vs fixed 48 h
    tau = json.load(open(ROOT / "personC" / "forecast" / "tau90.json"))
    # One change at a time: (a) only the worst-case time that sizes the reserve comes from the
    # forecaster, the restoration estimate stays at the utility's 24 h; (b) both come from it.
    settings = [("fixed 48 h / 24 h", 48, 24)]
    for key in ("typical", "large"):
        if key in tau:
            p90 = max(1, math.ceil(tau[key]["tau90_h"]))
            settings.append((f"forecast P90 only, {key} outage", p90, 24))
    if "typical" in tau:
        settings.append(("forecast P90 and median, typical outage", max(1, math.ceil(tau["typical"]["tau90_h"])),
                         max(1, math.ceil(tau["typical"]["tau50_h"]))))
    jobs = [(lab, p90, est, w, d, du) for (lab, p90, est), w, d, du in
            itertools.product(settings, (False, True), range(1, 29), (12, 24, 48, 72))]
    with Pool(6) as p:
        fr = pd.DataFrame(p.map(forecast_run, jobs, chunksize=8))
    fr.to_csv(OUT / "forecast_runs.csv", index=False)
    for w in (False, True):
        ref = fr[(fr.setting == settings[0][0]) & (fr.warning == w)].set_index(KEYS)[list(METRICS)]
        for lab, p90, est in settings[1:]:
            alt = fr[(fr.setting == lab) & (fr.warning == w)].set_index(KEYS)[list(METRICS)]
            rows += paired(f"Forecaster ({'warning' if w else 'no warning'})", "fixed P90 48 h, estimate 24 h",
                           f"{lab}: P90 {p90} h, estimate {est} h", ref, alt)
    # 5. warning vs no warning
    sh0 = base[(base.controller == "shield") & (~base.warning)].set_index(KEYS)[list(METRICS)]
    sh1 = base[(base.controller == "shield") & (base.warning)].set_index(KEYS)[list(METRICS)]
    rows += paired("24 h warning (shield)", "no warning", "warning", sh0, sh1)
    a, n = seed_mean(rl, "nowarn")
    b, _ = seed_mean(rl, "warn")
    rows += paired("24 h warning (learned policy)", "no warning", "warning", a, b, n)

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "ablations.csv", index=False)
    show = df.copy()
    for c in ("mean_A", "mean_B", "diff_B_minus_A", "ci_low", "ci_high"):
        show[c] = show[c].round(1)
    show["p"] = show.p.map(lambda x: f"{x:.2g}")
    show["95% CI"] = "[" + show.ci_low.astype(str) + ", " + show.ci_high.astype(str) + "]"
    show = show[["ablation", "A", "B", "metric", "n_outages", "seeds", "mean_A", "mean_B", "diff_B_minus_A", "95% CI", "p"]]
    (OUT / "results.md").write_text("# Step 7: ablations\n\nTest outages for learned policies: starts 21-28 July "
                                    "(n = 32); other rows: 28 starts x 4 lengths (n = 112).\n\n"
                                    + show.to_markdown(index=False) + "\n")
    print(show.to_string(index=False))


if __name__ == "__main__":
    main()
