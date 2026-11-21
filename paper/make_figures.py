"""Paper figures (IEEE column / page width) and tables, generated from the result files."""
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from caregrid.sim import Assets, community, load_inputs, run_normal, run_outage  # noqa: E402

OUT = ROOT / "paper"
(OUT / "figures").mkdir(exist_ok=True)
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e1"
BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"], "mathtext.fontset": "stix",
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8, "legend.fontsize": 7, "xtick.labelsize": 7,
    "ytick.labelsize": 7, "axes.edgecolor": "#bdbcb7", "axes.labelcolor": INK, "xtick.color": INK2,
    "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.5, "axes.axisbelow": True, "lines.linewidth": 1.4,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.02})
COL, PAGE = 3.45, 7.0

ph = pd.read_csv(ROOT / "results" / "scenarios.csv")
cl = pd.read_csv(ROOT / "results" / "citylearn" / "scenarios.csv")
ph_main = ph[(ph.experiment == "main") & (~ph.precharge)]
cl_main = cl[(cl.experiment == "main") & (~cl.precharge)]

# ---------------------------------------------------------------- Fig: duration (two stacked panels)
fig, axes = plt.subplots(2, 1, figsize=(COL, 3.3), sharex=True)
for ax, df, series, title in [
    (axes[0], ph_main, [("soft", "Priority as weight (greedy)", ORANGE, "-", "o"),
                        ("mpc", "Priority as weight (MPC)", AQUA, "-", "s"),
                        ("shield", "CareGrid shield (greedy)", BLUE, "-", "D"),
                        ("oracle", "Perfect-foresight bound", GRAY, "--", "")],
     "(a) Phoenix pilot (community battery)"),
    (axes[1], cl_main, [("soft", "Priority as weight (greedy)", ORANGE, "-", "o"),
                        ("shield", "CareGrid shield (greedy)", BLUE, "-", "D"),
                        ("medical_only", "Medical-only dispatch (bound)", GRAY, "--", "")],
     "(b) CityLearn v3, Austin (per-home batteries)")]:
    for c, lab, col, ls, mk in series:
        g = df[df.controller == c].groupby("duration_h").crit_device_hours_down.mean()
        ax.plot(g.index, g.values, ls, color=col, marker=mk, ms=3.5, label=lab)
    ax.set_title(title, loc="left", fontsize=8)
    ax.set_ylabel("Device-hours unpowered")
    ax.set_ylim(bottom=-5)
    ax.axvline(24, color=GRID, lw=0.8, zorder=0)
    ax.legend(frameon=False, loc="upper left", handlelength=1.8)
axes[1].set_xticks([12, 24, 48, 72])
axes[1].set_xlabel("True outage duration (h); restoration estimate 24 h")
fig.savefig(OUT / "fig_duration.pdf")
fig.savefig(OUT / "figures" / "Fig2_device_hours_by_duration.png", dpi=300)
plt.close(fig)

# ---------------------------------------------------------------- Fig: weight trade-off (Phoenix)
sw = ph[ph.experiment == "w_heat"]
o48 = ph_main[(ph_main.controller == "oracle") & (ph_main.duration_h == 48)]
fig, ax = plt.subplots(figsize=(COL, 2.35))
for c, lab, col, mk in [("soft", "Priority as weight (greedy)", ORANGE, "o"), ("mpc", "Priority as weight (MPC)", AQUA, "s"),
                        ("shield", "CareGrid shield (greedy)", BLUE, "D"),
                        ("mpc_p90_shield", "CareGrid shield + P90 MPC", INK2, "^")]:
    g = sw[sw.controller == c].groupby("w_heat")[["person_degree_hours", "crit_device_hours_down"]].mean()
    ax.plot(g.person_degree_hours / 1000, g.crit_device_hours_down, "-", color=col, marker=mk, ms=3.5, label=lab)
    if c in ("soft", "mpc"):
        for wv, r in g.iterrows():
            if wv in (0.25, 8) and r.crit_device_hours_down > 50:
                ax.annotate(f"$w$={wv:g}", (r.person_degree_hours / 1000, r.crit_device_hours_down), fontsize=6.5,
                            color=INK2, xytext=(-22, -2) if wv == 8 else (4, 4), textcoords="offset points")
ax.plot(o48.person_degree_hours.mean() / 1000, 0, "s", color=INK, ms=4.5, label="Perfect-foresight bound")
ax.set_xlabel(r"Heat exposure ($10^3$ person-degree-hours $>$26.7$^\circ$C)")
ax.set_ylabel("Device-hours unpowered")
ax.set_ylim(-15, 520)
ax.legend(frameon=False, loc="upper right", handlelength=1.8, bbox_to_anchor=(1.0, 1.0))
fig.savefig(OUT / "fig_tradeoff.pdf")
fig.savefig(OUT / "figures" / "Fig3_weight_tradeoff.png", dpi=300)
plt.close(fig)

# ---------------------------------------------------------------- Fig: case study (page width)
inp, a, blds = load_inputs(), Assets(), community()
states, _ = run_normal(inp, a, blds)
start = 24 * 19 + 14
soc0, tin0 = states[start]
hrs = np.arange(48)
fig, axes = plt.subplots(1, 3, figsize=(PAGE, 1.65))
for c, lab, col in [("soft", "Priority as weight", ORANGE), ("shield", "CareGrid shield", BLUE)]:
    tr = run_outage(inp, a, blds, start, 48, c, soc0, tin0)
    axes[0].plot(hrs, [h["soc"] * 100 for h in tr], color=col, label=lab)
    axes[1].plot(hrs, [h["buildings"][8]["tin"] for h in tr], color=col, label=lab)
    axes[2].step(hrs, [sum(b["devices_down"] for b in h["buildings"]) for h in tr], where="post", color=col, label=lab)
axes[1].plot(hrs, [inp["temp"][start + h] for h in hrs], "--", color=GRAY, lw=1, label="Outdoor air")
axes[1].axhline(32.2, color=INK2, lw=0.6, ls=":")
axes[0].axvline(24, color=INK2, lw=0.6, ls=":")
axes[0].text(24.8, 75, "restoration\nestimate", fontsize=6.5, color=INK2, va="top")
titles = ["(a) Community battery SoC (%)", "(b) Care-facility indoor temp. ($^\\circ$C)", "(c) Medical devices unpowered (of 12)"]
for ax, t in zip(axes, titles):
    ax.set_title(t, loc="left", fontsize=8)
    ax.set_xlabel("Hours since outage began")
    ax.set_xticks([0, 12, 24, 36, 48])
axes[0].set_ylim(0, 100)
axes[1].set_ylim(24, 50)
axes[2].set_ylim(-0.5, 12.5)
h0, l0 = axes[0].get_legend_handles_labels()
h1, l1 = axes[1].get_legend_handles_labels()
fig.legend(h0 + h1[2:], l0 + l1[2:], frameon=False, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.07))
fig.tight_layout(w_pad=1.2)
fig.savefig(OUT / "fig_case.pdf")
fig.savefig(OUT / "figures" / "Fig4_case_study.png", dpi=300)
plt.close(fig)

# ---------------------------------------------------------------- Table: main results
NAMES = [("equal", "Equal curtailment (status quo)"), ("rule", "Rule-based critical-first"),
         ("soft", "Priority as weight, greedy"), ("mpc", "Priority as weight, MPC"),
         ("mpc_hi", "\\quad MPC, critical weight $\\times$100"), ("mpc_p90", "\\quad MPC planned to P90"),
         ("shield", "\\textbf{CareGrid shield, greedy}"), ("mpc_shield", "\\textbf{CareGrid shield + MPC}"),
         ("mpc_p90_shield", "\\textbf{CareGrid shield + P90 MPC}"), ("medical_only", "Medical-only dispatch (bound)"),
         ("oracle", "Perfect-foresight optimum (bound)")]


def cell(df, c, k, fmt):
    s = df[df.controller == c]
    return fmt.format(s[k].mean()) if len(s) else "--"


rows = []
for c, name in NAMES:
    rows.append(f"{name} & {cell(ph_main, c, 'crit_device_hours_down', '{:.1f}')} & "
                f"{cell(ph_main, c, 'crit_served_pct', '{:.1f}')} & {cell(ph_main, c, 'person_hours_danger', '{:.0f}')} & "
                f"{cell(ph_main, c, 'person_degree_hours', '{:,.0f}')} & "
                f"{cell(cl_main, c, 'crit_device_hours_down', '{:.1f}')} & {cell(cl_main, c, 'crit_served_pct', '{:.1f}')} & "
                f"{cell(cl_main, c, 'person_hours_danger', '{:.0f}')} \\\\")
HEAD = r"""\begin{table*}[t]
\centering
\caption{Outage results without warning, pooled over 28 start days $\times$ 4 durations ($n=112$ per cell). Device-h: unpowered medical device-hours per outage. Crit.: critical energy served (\%). PH$_{32}$: person-hours indoors above 32.2$^\circ$C. PDH: person-degree-hours above 26.7$^\circ$C. --: not run on that platform.}
\label{tab:main}
\begin{tabular}{lrrrrrrr}
\toprule
 & \multicolumn{4}{c}{Phoenix community microgrid (Platform 1)} & \multicolumn{3}{c}{CityLearn v3, Austin (Platform 2)} \\
\cmidrule(lr){2-5}\cmidrule(lr){6-8}
Controller & Device-h & Crit.\ (\%) & PH$_{32}$ & PDH & Device-h & Crit.\ (\%) & PH$_{32}$ \\
\midrule
"""
TAIL = "\\bottomrule\n\\end{tabular}\n\\end{table*}\n"
body = "\n".join(rows).replace(",", "{,}").replace("as weight{,} ", "as weight, ").replace("shield{,} ", "shield, ").replace("MPC{,} ", "MPC, ")
(OUT / "table_main.tex").write_text(HEAD + body + "\n" + TAIL)

# numbers quoted in the text
ph_all = ph[ph.experiment == "main"]
facts = {
    "ph_soft_dev": ph_main[ph_main.controller == "soft"].crit_device_hours_down.mean(),
    "ph_equal_dev": ph_main[ph_main.controller == "equal"].crit_device_hours_down.mean(),
    "cl_soft_dev": cl_main[cl_main.controller == "soft"].crit_device_hours_down.mean(),
    "cl_shield_dev": cl_main[cl_main.controller == "shield"].crit_device_hours_down.mean(),
    "mpc_w2": sw[(sw.controller == "mpc") & (sw.w_heat == 2)].crit_device_hours_down.mean(),
    "mpc_w4": sw[(sw.controller == "mpc") & (sw.w_heat == 4)].crit_device_hours_down.mean(),
    "mpc_w1": sw[(sw.controller == "mpc") & (sw.w_heat == 1)].crit_device_hours_down.mean(),
    "n_phoenix": len(ph), "n_citylearn": len(cl),
}
print(json.dumps({k: round(float(v), 2) for k, v in facts.items()}, indent=1))
print("wrote paper/fig_duration.pdf, fig_tradeoff.pdf, fig_case.pdf, table_main.tex")
