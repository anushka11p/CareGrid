"""Turn results/scenarios.csv into results/summary.md, results/summary.json and figures/*.png."""
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import wilcoxon  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from caregrid.sim import Assets, community, load_inputs, run_normal, run_outage  # noqa: E402

RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
df = pd.read_csv(RES / "scenarios.csv")
main = df[df.experiment == "main"]

LABEL = {
    "equal": "Equal curtailment (status quo)",
    "rule": "Rule-based critical-first",
    "soft": "Priority as weight (greedy)",
    "shield": "CareGrid shield (greedy)",
    "mpc": "Priority as weight (MPC)",
    "mpc_hi": "MPC, critical weight x100",
    "mpc_p90": "MPC planned to P90 horizon",
    "mpc_shield": "CareGrid shield + MPC",
    "mpc_p90_shield": "CareGrid shield + P90 MPC",
    "oracle": "Perfect-foresight optimum (bound)",
}
ORDER = list(LABEL)
METRICS = [("crit_device_hours_down", "Medical device-hours without power", 0),
           ("crit_served_pct", "Critical energy served (%)", 1),
           ("person_hours_danger", "Person-hours indoors > 32.2 C", 0),
           ("person_degree_hours", "Person-degree-hours > 26.7 C", 0)]

# palette (dataviz reference instance, light mode)
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e1"
BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#a3a29c"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "grid.linewidth": 0.6, "axes.axisbelow": True, "figure.dpi": 150,
                     "savefig.bbox": "tight", "axes.titlesize": 11, "axes.titleweight": "bold"})
rng = np.random.default_rng(0)


def ci(x, n=4000):
    x = np.asarray(x, float)
    if len(x) == 0 or np.all(x == x[0]):
        return (x.mean(), x.mean()) if len(x) else (np.nan, np.nan)
    boots = rng.choice(x, (n, len(x))).mean(1)
    return tuple(np.percentile(boots, [2.5, 97.5]))


def fmt(x, dec):
    m = np.mean(x)
    lo, hi = ci(x)
    return f"{m:.{dec}f} [{lo:.{dec}f}, {hi:.{dec}f}]"


out_md, summary = [], {}
w = lambda s="": out_md.append(s)

# ------------------------------------------------------------- headline tables
for pre in (False, True):
    w(f"### Main results, {'WITH' if pre else 'without'} 24 h outage warning (all durations pooled, n = 112 per row)")
    w()
    w("| Controller | " + " | ".join(m[1] for m in METRICS) + " |")
    w("|---|" + "---|" * len(METRICS))
    for c in ORDER:
        sub = main[(main.controller == c) & (main.precharge == pre)]
        w(f"| {LABEL[c]} | " + " | ".join(fmt(sub[k], d) for k, _, d in METRICS) + " |")
        summary.setdefault("pooled", {}).setdefault(str(pre), {})[c] = {k: float(sub[k].mean()) for k, _, _ in METRICS}
    w()

w("### Medical device-hours without power, by true outage duration (no warning; mean over 28 start days)")
w()
w("| Controller | " + " | ".join(f"{d} h" for d in sorted(main.duration_h.unique())) + " |")
w("|---|" + "---|" * main.duration_h.nunique())
for c in ORDER:
    sub = main[(main.controller == c) & (~main.precharge)]
    g = sub.groupby("duration_h")["crit_device_hours_down"].mean()
    w(f"| {LABEL[c]} | " + " | ".join(f"{v:.1f}" for v in g) + " |")
    summary.setdefault("by_duration_crit", {})[c] = {int(k): float(v) for k, v in g.items()}
w()
w("### Person-degree-hours above 26.7 C, by true outage duration (no warning)")
w()
w("| Controller | " + " | ".join(f"{d} h" for d in sorted(main.duration_h.unique())) + " |")
w("|---|" + "---|" * main.duration_h.nunique())
for c in ORDER:
    sub = main[(main.controller == c) & (~main.precharge)]
    g = sub.groupby("duration_h")["person_degree_hours"].mean()
    w(f"| {LABEL[c]} | " + " | ".join(f"{v:.0f}" for v in g) + " |")
    summary.setdefault("by_duration_heat", {})[c] = {int(k): float(v) for k, v in g.items()}
w()

# ------------------------------------------------------------- paired tests
w("### Paired comparisons (Wilcoxon signed-rank over matched scenarios, no warning, all durations)")
w()
w("| Comparison | Metric | Mean A | Mean B | Mean B - A | p |")
w("|---|---|---|---|---|---|")
pairs = [("soft", "shield"), ("mpc", "mpc_shield"), ("mpc", "mpc_p90"), ("mpc_p90", "mpc_p90_shield"), ("mpc", "mpc_hi")]
keys = ["day", "duration_h"]
summary["tests"] = []
for a, b in pairs:
    A = main[(main.controller == a) & (~main.precharge)].set_index(keys).sort_index()
    B = main[(main.controller == b) & (~main.precharge)].set_index(keys).sort_index()
    for k in ("crit_device_hours_down", "person_degree_hours"):
        d = B[k] - A[k]
        p = wilcoxon(A[k], B[k]).pvalue if np.any(d != 0) else 1.0
        w(f"| {LABEL[a]} (A) vs {LABEL[b]} (B) | {k} | {A[k].mean():.1f} | {B[k].mean():.1f} | {d.mean():+.1f} | {p:.2g} |")
        summary["tests"].append({"a": a, "b": b, "metric": k, "mean_a": float(A[k].mean()),
                                 "mean_b": float(B[k].mean()), "p": float(p)})
w()

# ------------------------------------------------------------- warning ablation
w("### Value of a 24 h outage warning (pre-charge), mean over all scenarios")
w()
w("| Controller | Device-hours down: no warning | with warning | Person-degree-hours: no warning | with warning |")
w("|---|---|---|---|---|")
for c in ORDER:
    s0 = main[(main.controller == c) & (~main.precharge)]
    s1 = main[(main.controller == c) & (main.precharge)]
    w(f"| {LABEL[c]} | {s0.crit_device_hours_down.mean():.1f} | {s1.crit_device_hours_down.mean():.1f} | "
      f"{s0.person_degree_hours.mean():.0f} | {s1.person_degree_hours.mean():.0f} |")
pc = main[main.precharge].drop_duplicates("day")
w()
w(f"Battery state of charge at outage start: {main[~main.precharge].soc0.mean() * 100:.0f}% without warning, "
  f"{main[main.precharge].soc0.mean() * 100:.0f}% with warning. Pre-charging draws "
  f"{pc.precharge_extra_grid_kwh.mean():.0f} kWh extra from the grid per event.")
w()
summary["soc0"] = {"no_warning": float(main[~main.precharge].soc0.mean()), "warning": float(main[main.precharge].soc0.mean()),
                   "precharge_extra_grid_kwh": float(pc.precharge_extra_grid_kwh.mean())}

# ------------------------------------------------------------- sweeps
def sweep_table(exp, param, label, ctrls, dur=None):
    s = df[df.experiment == exp]
    if dur is not None:
        s = s[s.duration_h == dur]
    w(f"| Controller | {label} | Device-hours down | Person-degree-hours |")
    w("|---|---|---|---|")
    res = {}
    for c in ctrls:
        for v, g in s[s.controller == c].groupby(param):
            w(f"| {LABEL[c]} | {v:g} | {g.crit_device_hours_down.mean():.1f} | {g.person_degree_hours.mean():.0f} |")
            res.setdefault(c, {})[float(v)] = [float(g.crit_device_hours_down.mean()), float(g.person_degree_hours.mean())]
    w()
    return res


w("### Battery size sweep (48 h outage, no warning)")
w()
summary["battery"] = sweep_table("battery", "batt_kwh", "Battery kWh", ["rule", "soft", "shield", "mpc", "mpc_p90", "mpc_p90_shield", "oracle"])
w("### Heat-weight sweep (48 h outage, no warning)")
w()
summary["w_heat"] = sweep_table("w_heat", "w_heat", "Heat weight", ["soft", "shield", "mpc", "mpc_p90_shield"])
w("### Shield P90 bound sensitivity (no warning; 72 h true outage, utility estimate 24 h)")
w()
summary["p90"] = sweep_table("p90", "p90_h", "P90 bound (h)", ["shield", "mpc_p90_shield"], dur=72)
w("### Outage start-hour sensitivity (48 h outage, no warning)")
w()
summary["start_hour"] = sweep_table("start_hour", "start_hour", "Start hour", ["rule", "soft", "shield", "mpc", "mpc_p90", "mpc_p90_shield", "oracle"])

gm = json.loads((RES / "grid_month.json").read_text())
summary["grid_month"] = gm
w("### Grid-connected July 2023 (normal operation)")
w()
for k, v in gm.items():
    w(f"- {k}: {v:,.1f}")
(RES / "summary.md").write_text("\n".join(out_md) + "\n")
(RES / "summary.json").write_text(json.dumps(summary, indent=1))

# ------------------------------------------------------------- figures
nw = main[~main.precharge]

# F1: duration curves (two panels, one axis each)
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
series = [("soft", "Priority as weight (greedy)", ORANGE, "-"),
          ("mpc", "Priority as weight (MPC)", AQUA, "-"),
          ("shield", "CareGrid shield (greedy)", BLUE, "-"),
          ("oracle", "Perfect-foresight bound", GRAY, "--")]
for ax, (k, title) in zip(axes, [("crit_device_hours_down", "Medical device-hours without power"),
                                  ("person_degree_hours", "Heat exposure (person-degree-hours > 26.7 C)")]):
    for c, lab, col, ls in series:
        g = nw[nw.controller == c].groupby("duration_h")[k].mean()
        ax.plot(g.index, g.values, ls, color=col, lw=2, marker="o", ms=5, label=lab)
    ax.set_title(title, loc="left", color=INK)
    ax.set_xlabel("True outage duration (h)")
    ax.set_xticks([12, 24, 48, 72])
    ax.axvline(24, color=GRID, lw=1, zorder=0)
    ax.set_ylim(bottom=0)
axes[0].legend(frameon=False, fontsize=8.5, loc="upper left")
fig.text(0.01, -0.04, "All controllers are told restoration takes 24 h (grey line); shields reserve to a 48 h worst case. Mean of 28 start days, no warning.",
         fontsize=8.5, color=INK2)
fig.savefig(FIG / "f1_duration.png")
plt.close(fig)

# F2: headline bars (48 h, no warning)
s48 = nw[nw.duration_h == 48]
ctrls = ["equal", "rule", "soft", "mpc", "mpc_p90", "shield", "mpc_p90_shield", "oracle"]
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
for ax, (k, title) in zip(axes, [("crit_device_hours_down", "Medical device-hours without power"),
                                  ("person_hours_danger", "Person-hours indoors above 32.2 C")]):
    means = [s48[s48.controller == c][k].mean() for c in ctrls]
    cis = [ci(s48[s48.controller == c][k]) for c in ctrls]
    cols = [BLUE if "shield" in c else GRAY for c in ctrls]
    y = np.arange(len(ctrls))[::-1]
    ax.barh(y, means, color=cols, height=0.6,
            xerr=[[m - lo for m, (lo, hi) in zip(means, cis)], [hi - m for m, (lo, hi) in zip(means, cis)]],
            error_kw={"ecolor": INK2, "lw": 1, "capsize": 2})
    for yi, m, (lo, hi) in zip(y, means, cis):
        ax.text(max(m, hi), yi, f"  {m:.0f}", va="center", ha="left", fontsize=8.5, color=INK)
    ax.set_yticks(y)
    ax.set_yticklabels([LABEL[c] for c in ctrls] if ax is axes[0] else [])
    ax.set_title(title, loc="left", color=INK)
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, max(hi for _, hi in cis) * 1.15)
fig.suptitle("48 h outage from 14:00, July 2023 Phoenix weather (mean, 95% CI over 28 start days)",
             x=0.01, ha="left", fontsize=9, color=INK2, y=1.0)
fig.savefig(FIG / "f2_headline_48h.png")
plt.close(fig)

# F3: trade-off frontier from the heat-weight sweep
sw = df[df.experiment == "w_heat"]
fig, ax = plt.subplots(figsize=(6, 4.2))
for c, lab, col in [("soft", "Priority as weight (greedy)", ORANGE), ("mpc", "Priority as weight (MPC)", AQUA),
                    ("shield", "CareGrid shield (greedy)", BLUE)]:
    g = sw[sw.controller == c].groupby("w_heat")[["person_degree_hours", "crit_device_hours_down"]].mean()
    ax.plot(g.person_degree_hours, g.crit_device_hours_down, "-", color=col, lw=2, marker="o", ms=6, label=lab)
    for wv, r in g.iterrows():
        if c != "shield" and wv in (0.25, 8) and r.crit_device_hours_down > 50:
            ax.annotate(f"w={wv:g}", (r.person_degree_hours, r.crit_device_hours_down), fontsize=8, color=INK2,
                        xytext=(4, 4), textcoords="offset points")
o = s48[s48.controller == "oracle"]
ax.plot(o.person_degree_hours.mean(), o.crit_device_hours_down.mean(), "s", color=INK, ms=7, label="Perfect-foresight bound")
ax.set_xlabel("Heat exposure (person-degree-hours > 26.7 C)  ->  worse")
ax.set_ylabel("Medical device-hours without power  ->  worse")
ax.set_title("Priority as a weight: safe only inside a narrow weight band", loc="left", color=INK)
ax.text(0.99, 0.04, "markers = heat weight 0.25 ... 8 (48 h outages)", transform=ax.transAxes, ha="right", fontsize=8, color=INK2)
ax.legend(frameon=False, fontsize=8.5)
ax.set_ylim(bottom=-3)
fig.savefig(FIG / "f3_tradeoff.png")
plt.close(fig)

# F4: case study, hottest start (19 July 14:00, 48 h)
inp, a, blds = load_inputs(), Assets(), community()
states, _ = run_normal(inp, a, blds)
start = 24 * 19 + 14
soc0, tin0 = states[start]
fig, axes = plt.subplots(3, 1, figsize=(9, 7), sharex=True, gridspec_kw={"height_ratios": [1, 1.2, 0.8]})
hrs = np.arange(48)
for c, lab, col in [("soft", "Priority as weight (greedy)", ORANGE), ("shield", "CareGrid shield (greedy)", BLUE)]:
    tr = run_outage(inp, a, blds, start, 48, c, soc0, tin0)
    axes[0].plot(hrs, [h["soc"] * 100 for h in tr], color=col, lw=2, label=lab)
    axes[1].plot(hrs, [h["buildings"][8]["tin"] for h in tr], color=col, lw=2, label=f"{lab}: care facility")
    down = [sum(b["devices_down"] for b in h["buildings"]) for h in tr]
    axes[2].step(hrs, down, where="post", color=col, lw=2, label=lab)
axes[1].plot(hrs, [inp["temp"][start + h] for h in hrs], color=GRAY, lw=1.5, ls="--", label="Outdoor air (real, Open-Meteo)")
axes[1].axhline(32.2, color=INK2, lw=0.8, ls=":")
axes[1].text(47, 32.4, "32.2 C extreme caution", ha="right", fontsize=8, color=INK2)
axes[0].axvline(24, color=INK2, lw=0.8, ls=":")
axes[0].text(24.3, 3, "utility's estimated restoration", fontsize=8, color=INK2)
axes[0].set_ylabel("Battery SoC (%)")
axes[0].set_ylim(0, 100)
axes[1].set_ylabel("Temperature (C)")
axes[2].set_ylabel("Medical devices\nwithout power")
axes[2].set_xlabel("Hours since outage began (19 July 2023, 14:00, Phoenix)")
axes[0].set_title("Case study: the hottest outage of July 2023, 48 h", loc="left", color=INK)
axes[0].legend(frameon=False, fontsize=8, loc="upper right")
axes[1].set_ylim(24, 54)
axes[1].legend(frameon=False, fontsize=8, loc="upper center", ncol=3)
axes[2].legend(frameon=False, fontsize=8, loc="upper left")
fig.savefig(FIG / "f4_case_study.png")
plt.close(fig)

# F5: battery sweep
sb = df[df.experiment == "battery"]
fig, ax = plt.subplots(figsize=(6, 4))
for c, lab, col, ls in [("rule", "Rule-based critical-first", GRAY, "-"), ("mpc", "Priority as weight (MPC)", ORANGE, "-"),
                        ("shield", "CareGrid shield (greedy)", BLUE, "-")]:
    g = sb[sb.controller == c].groupby("batt_kwh").crit_device_hours_down.mean()
    ax.plot(g.index, g.values, ls, color=col, lw=2, marker="o", ms=5, label=lab)
ax.set_xlabel("Community battery (kWh) for 9 buildings, 60 kWp PV")
ax.set_ylabel("Medical device-hours without power")
ax.set_title("Battery size vs medical-device outages (48 h)", loc="left", color=INK)
ax.legend(frameon=False, fontsize=8.5)
ax.set_ylim(bottom=0)
fig.savefig(FIG / "f5_battery.png")
plt.close(fig)
print("wrote results/summary.md, results/summary.json, figures/f1-f5")
