"""Summarise the CityLearn run: results/citylearn/summary.md, summary.json, figures/f6-f7."""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import wilcoxon  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES, FIG = ROOT / "results" / "citylearn", ROOT / "figures"
df = pd.read_csv(RES / "scenarios.csv")
main = df[df.experiment == "main"]
LABEL = {"equal": "Equal curtailment (status quo)", "rule": "Rule-based critical-first",
         "soft": "Priority as weight (greedy)", "shield": "CareGrid shield (greedy)",
         "medical_only": "Medical-only dispatch (bound for medical service)"}
ORDER = list(LABEL)
METRICS = [("crit_device_hours_down", "Medical device-hours without power", 1),
           ("crit_served_pct", "Critical energy served (%)", 1),
           ("person_hours_danger", "Person-hours indoors > 32.2 C", 0),
           ("person_degree_hours", "Person-degree-hours > 26.7 C", 0),
           ("essential_kwh_unserved", "Essential-circuit kWh not served", 1)]
rng = np.random.default_rng(0)
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e1"
BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#a3a29c"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True, "figure.dpi": 150,
                     "savefig.bbox": "tight", "axes.titlesize": 11, "axes.titleweight": "bold"})


def ci(x, n=4000):
    x = np.asarray(x, float)
    if np.all(x == x[0]):
        return x[0], x[0]
    b = rng.choice(x, (n, len(x))).mean(1)
    return tuple(np.percentile(b, [2.5, 97.5]))


def fmt(x, d):
    lo, hi = ci(x)
    return f"{np.mean(x):.{d}f} [{lo:.{d}f}, {hi:.{d}f}]"


md, summary = [], {}
w = md.append
for pre in (False, True):
    w(f"### CityLearn main results, {'WITH' if pre else 'without'} 24 h warning (all durations pooled, n = 112 per row)\n")
    w("| Controller | " + " | ".join(m[1] for m in METRICS) + " |")
    w("|---|" + "---|" * len(METRICS))
    for c in ORDER:
        s = main[(main.controller == c) & (main.precharge == pre)]
        w(f"| {LABEL[c]} | " + " | ".join(fmt(s[k], d) for k, _, d in METRICS) + " |")
        summary.setdefault("pooled", {}).setdefault(str(pre), {})[c] = {k: float(s[k].mean()) for k, _, _ in METRICS}
    w("")

nw = main[~main.precharge]
for k, title, dec in [("crit_device_hours_down", "Medical device-hours without power", 1),
                      ("person_hours_danger", "Person-hours indoors above 32.2 C", 0)]:
    w(f"### {title}, by true outage duration (no warning; mean of 28 start days)\n")
    durs = sorted(nw.duration_h.unique())
    w("| Controller | " + " | ".join(f"{d} h" for d in durs) + " |")
    w("|---|" + "---|" * len(durs))
    for c in ORDER:
        g = nw[nw.controller == c].groupby("duration_h")[k].mean()
        w(f"| {LABEL[c]} | " + " | ".join(f"{v:.{dec}f}" for v in g) + " |")
        summary.setdefault(f"by_duration_{k}", {})[c] = {int(a): float(b) for a, b in g.items()}
    w("")

w("### Paired comparison, priority-as-weight vs CareGrid shield (Wilcoxon, no warning, all durations)\n")
w("| Metric | Weight | Shield | Shield - weight | p |")
w("|---|---|---|---|---|")
A = nw[nw.controller == "soft"].set_index(["day", "duration_h"]).sort_index()
B = nw[nw.controller == "shield"].set_index(["day", "duration_h"]).sort_index()
summary["tests"] = {}
for k in ("crit_device_hours_down", "person_hours_danger", "person_degree_hours", "essential_kwh_unserved"):
    d = B[k] - A[k]
    p = wilcoxon(A[k], B[k]).pvalue if np.any(d != 0) else 1.0
    w(f"| {k} | {A[k].mean():.1f} | {B[k].mean():.1f} | {d.mean():+.1f} | {p:.2g} |")
    summary["tests"][k] = {"soft": float(A[k].mean()), "shield": float(B[k].mean()), "p": float(p)}
w("")

for exp, param, label, ctrls in [("w_heat", "w_heat", "Heat weight", ["soft", "shield"]),
                                 ("battery", "batt_kwh", "Battery kWh per home", ORDER)]:
    s = df[df.experiment == exp]
    w(f"### Sweep: {label} (48 h outage, no warning)\n")
    w(f"| Controller | {label} | Device-hours down | Person-hours > 32.2 C | Essential kWh not served |")
    w("|---|---|---|---|---|")
    for c in ctrls:
        for v, g in s[s.controller == c].groupby(param):
            w(f"| {LABEL[c]} | {v:g} | {g.crit_device_hours_down.mean():.1f} | {g.person_hours_danger.mean():.0f} | {g.essential_kwh_unserved.mean():.1f} |")
            summary.setdefault(exp, {}).setdefault(c, {})[float(v)] = [float(g.crit_device_hours_down.mean()),
                                                                       float(g.person_hours_danger.mean())]
    w("")

w("### Model-validity checks\n")
w(f"- Plan-vs-CityLearn mismatch (grid import the controller did not plan, counted against medical devices): "
  f"mean {main.infeasible_kwh.mean():.2f} kWh per outage, max {main.infeasible_kwh.max():.1f} kWh.")
w(f"- Highest indoor temperature predicted by the LSTM in any run: {df.max_tin.max():.1f} C "
  f"(medical-only dispatch, cooling off). Runs with indoor peaks above 40 C: "
  f"{(df.max_tin > 40).mean() * 100:.0f}% of all episodes, concentrated in controllers that shed cooling longest.")
(RES / "summary.md").write_text("\n".join(md) + "\n")
(RES / "summary.json").write_text(json.dumps(summary, indent=1))

# F6: duration curves on CityLearn
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
for ax, (k, title) in zip(axes, [("crit_device_hours_down", "Medical device-hours without power"),
                                  ("person_hours_danger", "Person-hours indoors > 32.2 C")]):
    for c, col, ls in [("equal", GRAY, ":"), ("soft", ORANGE, "-"), ("shield", BLUE, "-"), ("medical_only", INK2, "--")]:
        g = nw[nw.controller == c].groupby("duration_h")[k].mean()
        ax.plot(g.index, g.values, ls, color=col, lw=2, marker="o", ms=5, label=LABEL[c])
    ax.set_title(title, loc="left", color=INK)
    ax.set_xlabel("True outage duration (h)")
    ax.set_xticks([12, 24, 48, 72])
    ax.set_ylim(bottom=0)
axes[0].legend(frameon=False, fontsize=8, loc="upper left")
fig.text(0.01, -0.04, "CityLearn v3, tx_travis_county_neighborhood: 10 ResStock homes, Austin TX, July 2018 weather, "
         "LSTM indoor temperatures. Mean of 28 start days, no warning.", fontsize=8.5, color=INK2)
fig.savefig(FIG / "f6_citylearn_duration.png")
plt.close(fig)

# F7: heat-weight trade-off on CityLearn
sw = df[df.experiment == "w_heat"]
fig, ax = plt.subplots(figsize=(6, 4.2))
for c, col in [("soft", ORANGE), ("shield", BLUE)]:
    g = sw[sw.controller == c].groupby("w_heat")[["person_hours_danger", "crit_device_hours_down"]].mean()
    ax.plot(g.person_hours_danger, g.crit_device_hours_down, "-", color=col, lw=2, marker="o", ms=6, label=LABEL[c])
    for wv, r in g.iterrows():
        if c == "soft" and wv in (0.25, 8):
            ax.annotate(f"w={wv:g}", (r.person_hours_danger, r.crit_device_hours_down), fontsize=8, color=INK2,
                        xytext=(4, 4), textcoords="offset points")
ax.set_xlabel("Person-hours indoors > 32.2 C  ->  worse")
ax.set_ylabel("Medical device-hours without power  ->  worse")
ax.set_title("CityLearn: heat weight vs medical outages (48 h)", loc="left", color=INK)
ax.legend(frameon=False, fontsize=8.5)
ax.set_ylim(bottom=-3)
fig.savefig(FIG / "f7_citylearn_tradeoff.png")
plt.close(fig)
print("wrote results/citylearn/summary.md, figures/f6-f7")
