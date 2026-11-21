"""Step 6 report: MAPPO-Lagrangian on CityLearn, tables and training curves."""
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import wilcoxon  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
RES = HERE / "results"
K = {"crit_device_hours_down": "Device-h lost", "person_hours_danger": "Person-h > 32.2 C",
     "vuln_degree_hours": "Vuln.-weighted degree-h", "essential_kwh_unserved": "Essential kWh unserved",
     "infeasible_kwh": "Unplanned import kWh"}
NAMES = {"soft": "Priority as weight (greedy)", "shield": "Shield (greedy, citylearn_port)",
         "shield_fixed_pacing": "Shield, fixed pacing (policy path)", "medical_only": "Medical-only dispatch (bound)",
         "mappo_shield": "Shield + MAPPO-Lag."}


def main():
    ev, tr = pd.read_csv(RES / "eval.csv"), pd.read_csv(RES / "training.csv")
    rows = []
    for c in ("soft", "shield", "shield_fixed_pacing", "mappo_shield", "medical_only"):
        g = ev[ev.controller == c]
        if g.empty:
            continue
        ps = g.groupby("seed")[list(K)].mean()
        fmt = (lambda k: f"{ps[k].mean():,.1f} ± {ps[k].std():,.1f}") if len(ps) > 1 else (lambda k: f"{ps[k].mean():,.1f}")
        rows.append({"controller": NAMES[c], "seeds": len(ps), **{v: fmt(k) for k, v in K.items()}})
    tab = pd.DataFrame(rows)
    sh = ev[ev.controller == "shield_fixed_pacing"].set_index(["day", "duration_h"]).sort_index()
    rl = ev[ev.controller == "mappo_shield"].groupby(["day", "duration_h"]).mean(numeric_only=True).loc[sh.index]
    tests = []
    for k, v in K.items():
        if k == "infeasible_kwh":
            continue
        d = rl[k] - sh[k]
        p = wilcoxon(sh[k], rl[k]).pvalue if np.any(d != 0) else 1.0
        tests.append({"metric": v, "fixed pacing": round(sh[k].mean(), 1), "MAPPO": round(rl[k].mean(), 1),
                      "change %": round(100 * (rl[k].mean() / sh[k].mean() - 1), 1) if sh[k].mean() else 0.0, "p": f"{p:.2g}"})
    by = ev[ev.controller.isin(["shield_fixed_pacing", "mappo_shield", "soft"])].groupby(
        ["controller", "duration_h"]).vuln_degree_hours.mean().unstack().round(0)
    fin = tr.sort_values("episodes").groupby("seed").tail(1)[["seed", "episodes", "mean_cost", "cost_limit", "lambda", "mean_release", "minutes"]]
    md = ("# Step 6: MAPPO-Lagrangian on CityLearn v3 (10 Austin homes)\n\n"
          "One shared actor per home on local observations, centralised reward and cost critics on all homes. "
          "Trained on outages starting 1-20 July 2018, tested on unseen starts 21-28 July (12/24/48/72 h, n = 32), "
          "no warning. Learned rows: mean ± s.d. over seeds.\n\n" + tab.to_markdown(index=False)
          + "\n\nThe two shield rows must agree: the fixed-pacing release through the MAPPO code path reproduces "
          "citylearn_port's greedy shield.\n\n## MAPPO vs fixed pacing (paired over test outages, seeds averaged)\n\n"
          + pd.DataFrame(tests).to_markdown(index=False)
          + "\n\n## Vulnerability-weighted degree-hours by outage length\n\n" + by.to_markdown()
          + "\n\n## End of training\n\n" + fin.round(2).to_markdown(index=False) + "\n")
    (HERE / "results.md").write_text(md)

    fig, axes = plt.subplots(3, 1, figsize=(6, 6), sharex=True)
    for seed, g in tr.groupby("seed"):
        g = g.sort_values("episodes")
        axes[0].plot(g.episodes, g.mean_cost, lw=1.1, label=f"seed {seed}")
        axes[1].plot(g.episodes, g["lambda"], lw=1.1)
        axes[2].plot(g.episodes, g.mean_release, lw=1.1)
    axes[0].plot(tr.sort_values("episodes").episodes, tr.sort_values("episodes").cost_limit, color="#52514e", ls=":", lw=1, label="cost limit")
    axes[0].set_ylabel("Person-h > 32.2 C\nper hour")
    axes[1].set_ylabel("Lagrange multiplier")
    axes[2].set_ylabel("Mean release rate")
    axes[2].set_xlabel("Training outages")
    axes[0].legend(frameon=False, fontsize=7)
    for ax in axes:
        ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(HERE / "training_curves.png", dpi=200)
    print(md)


if __name__ == "__main__":
    main()
