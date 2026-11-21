"""Figures and tables for the team paper, generated from the result files (no typed numbers).

Writes paper_team/fig_*.pdf, paper_team/figures/*.png, paper_team/tab_*.tex and facts.json.
Run from the project root with the main environment: .venv/bin/python paper_team/make_paper.py
"""
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from caregrid.sim import Assets, community, load_inputs, run_normal, run_outage  # noqa: E402

OUT = ROOT / "paper_team"
(OUT / "figures").mkdir(exist_ok=True)
INK2, GRID = "#52514e", "#e6e5e1"
BLUE, ORANGE, AQUA, GRAY, PURPLE = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984", "#6b5bd6"
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"], "mathtext.fontset": "stix",
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8, "legend.fontsize": 7, "xtick.labelsize": 7,
    "ytick.labelsize": 7, "axes.edgecolor": "#bdbcb7", "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.5, "axes.axisbelow": True, "lines.linewidth": 1.4, "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02})
COL, PAGE = 3.45, 7.0
F = {}


def save(fig, name):
    fig.savefig(OUT / f"fig_{name}.pdf")
    fig.savefig(OUT / "figures" / f"fig_{name}.png", dpi=300)
    plt.close(fig)


def tex_p(p):
    if p >= 0.001:
        return f"{p:.2g}"
    m, e = f"{p:.0e}".split("e")
    return f"${m}\\times10^{{{int(e)}}}$"


def tex_num(x, d=1):
    s = f"{x:,.{d}f}".replace(",", "{,}")
    if s.lstrip("-").replace("{,}", "").replace(".", "").strip("0") == "":
        s = s.lstrip("-")                               # no "-0.0"
    return s.replace("-", "$-$")


# ---------------------------------------------------------------- data
sc = pd.read_csv(ROOT / "results" / "scenarios.csv")
main = sc[(sc.experiment == "main") & (~sc.precharge)]
mainw = sc[(sc.experiment == "main") & (sc.precharge)]
cl = pd.read_csv(ROOT / "results" / "citylearn" / "scenarios.csv")
clm = cl[(cl.experiment == "main") & (~cl.precharge)]
ht = pd.read_csv(ROOT / "personC" / "step3" / "ablation.csv")
fc_pred = pd.read_csv(ROOT / "personC" / "forecast" / "test_predictions.csv")
fc_ev = pd.read_csv(ROOT / "personC" / "forecast" / "events.csv")
tau = json.load(open(ROOT / "personC" / "forecast" / "tau90.json"))
rl = pd.read_csv(ROOT / "personC" / "phoenix_rl" / "results" / "eval.csv")
rlb = pd.read_csv(ROOT / "personC" / "phoenix_rl" / "results" / "baselines.csv")
ma = pd.read_csv(ROOT / "personC" / "citylearn_rl" / "results" / "eval.csv")
ab = pd.read_csv(ROOT / "personC" / "step7" / "ablations.csv")
rob = pd.read_csv(ROOT / "personC" / "step7" / "robustness.csv")
summ = json.load(open(ROOT / "results" / "summary.json"))

# ---------------------------------------------------------------- facts used in the text
def m(df, c, k):
    return float(df[df.controller == c][k].mean())


F["ph"] = {c: {k: m(main, c, k) for k in ("crit_device_hours_down", "crit_served_pct", "person_hours_danger",
                                           "person_degree_hours", "vuln_degree_hours")}
           for c in main.controller.unique()}
F["ph_warn"] = {c: {k: m(mainw, c, k) for k in ("crit_device_hours_down", "person_hours_danger", "person_degree_hours")}
                for c in mainw.controller.unique()}
F["ph_tests"] = summ["tests"]
F["w_heat_mpc"] = summ["w_heat"]["mpc"]
F["cl"] = {c: {k: m(clm, c, k) for k in ("crit_device_hours_down", "crit_served_pct", "person_hours_danger",
                                          "person_degree_hours")} for c in clm.controller.unique()}
F["cl_by_dur"] = clm.groupby(["controller", "duration_h"]).crit_device_hours_down.mean().unstack().round(1).to_dict("index")
F["ph_by_dur"] = main.groupby(["controller", "duration_h"]).crit_device_hours_down.mean().unstack().round(1).to_dict("index")
F["forecast"] = {"events": int(len(fc_ev)), "train_events": int(fc_ev.year.between(2015, 2021).sum()),
                 "test_events": int(fc_ev.year.isin([2023, 2024]).sum()),
                 "coverage_p90": float((fc_pred.duration_h <= fc_pred.p90_h).mean()),
                 "coverage_p50": float((fc_pred.duration_h <= fc_pred.p50_h).mean()),
                 "median_h": float(fc_ev.duration_h.median()), "p90_h": float(fc_ev.duration_h.quantile(0.9)),
                 "max_h": float(fc_ev.duration_h.max()), **tau}
fres = (ROOT / "personC" / "forecast" / "results.md").read_text()
F["forecast"]["results_md"] = fres
F["ablations"] = ab.to_dict("records")
F["robust"] = rob.groupby(["factor", "level", "controller", "duration_h"])[
    ["crit_device_hours_down", "person_hours_danger"]].mean().reset_index().to_dict("records")


def seeds(df, c, k):
    g = df[df.controller == c].groupby("seed")[k].mean()
    return float(g.mean()), float(g.std()), int(len(g))


F["rl"] = {}
for c in rl.controller.unique():
    F["rl"][c] = {k: seeds(rl, c, k) for k in ("crit_device_hours_down", "person_hours_danger", "vuln_degree_hours")}
for w in (False, True):
    for c in rlb[rlb.warning == w].controller.unique():
        g = rlb[(rlb.warning == w) & (rlb.controller == c)]
        F["rl"][f"{c}|{'warn' if w else 'nowarn'}"] = {k: (float(g[k].mean()), 0.0, 1) for k in
                                                      ("crit_device_hours_down", "person_hours_danger", "vuln_degree_hours")}
F["rl_by_dur"] = rl.groupby(["controller", "duration_h"]).vuln_degree_hours.mean().unstack().round(0).to_dict("index")
F["rl_shield_by_dur"] = rlb[rlb.controller == "shield"].groupby(["warning", "duration_h"]).vuln_degree_hours.mean().unstack().round(0).to_dict("index")
F["mappo"] = {c: {k: seeds(ma, c, k) for k in ("crit_device_hours_down", "person_hours_danger", "vuln_degree_hours",
                                                 "essential_kwh_unserved")} for c in ma.controller.unique()}
F["mappo_by_dur"] = ma.groupby(["controller", "duration_h"]).vuln_degree_hours.mean().unstack().round(0).to_dict("index")
(OUT / "facts.json").write_text(json.dumps(F, indent=1, default=str))

# ---------------------------------------------------------------- Fig: duration curves (Phoenix, CityLearn)
fig, axes = plt.subplots(2, 1, figsize=(COL, 3.3), sharex=True)
for ax, df, series, title in [
    (axes[0], main, [("soft", "Priority as weight (greedy)", ORANGE, "-", "o"), ("mpc", "Priority as weight (MPC)", AQUA, "-", "s"),
                     ("shield", "CareGrid shield", BLUE, "-", "D"), ("oracle", "Perfect-foresight bound", GRAY, "--", "")],
     "(a) Phoenix community microgrid"),
    (axes[1], clm, [("soft", "Priority as weight (greedy)", ORANGE, "-", "o"), ("shield", "CareGrid shield (base)", BLUE, "-", "D"),
                    ("medical_only", "Medical-only dispatch (bound)", GRAY, "--", "")],
     "(b) CityLearn v3, Austin homes")]:
    for c, lab, col, ls, mk in series:
        g = df[df.controller == c].groupby("duration_h").crit_device_hours_down.mean()
        ax.plot(g.index, g.values, ls, color=col, marker=mk, ms=3.5, label=lab)
    ax.set_title(title, loc="left")
    ax.set_ylabel("Device-hours unpowered")
    ax.set_ylim(bottom=-5)
    ax.legend(frameon=False, loc="upper left", handlelength=1.8)
axes[1].set_xticks([12, 24, 48, 72])
axes[1].set_xlabel("True outage duration (h); restoration estimate 24 h")
save(fig, "duration")

# ---------------------------------------------------------------- Fig: case study
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
for ax, t in zip(axes, ["(a) Community battery SoC (%)", "(b) Care-facility indoor temp. ($^\\circ$C)",
                        "(c) Medical devices unpowered (of 12)"]):
    ax.set_title(t, loc="left")
    ax.set_xlabel("Hours since outage began")
    ax.set_xticks([0, 12, 24, 36, 48])
axes[0].set_ylim(0, 100)
axes[1].set_ylim(24, 50)
axes[2].set_ylim(-0.5, 12.5)
h0, l0 = axes[0].get_legend_handles_labels()
h1, l1 = axes[1].get_legend_handles_labels()
fig.legend(h0 + h1[2:], l0 + l1[2:], frameon=False, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.07))
fig.tight_layout(w_pad=1.2)
save(fig, "case")

# ---------------------------------------------------------------- Fig: forecaster
fig, axes = plt.subplots(1, 2, figsize=(COL, 1.75), gridspec_kw={"width_ratios": [1.2, 1]})
ax = axes[0]
bins = np.logspace(np.log10(0.25), np.log10(300), 40)
ax.hist(fc_ev.duration_h, bins=bins, color=BLUE, alpha=0.8)
ax.set_xscale("log")
ax.axvline(48, color=ORANGE, lw=1, ls="--")
ax.text(52, ax.get_ylim()[1] * 0.85, "48 h\nassumed", fontsize=6.5, color=ORANGE, va="top")
ax.set_xlabel("Outage duration (h)")
ax.set_ylabel("Events")
ax.set_title(f"(a) {len(fc_ev):,} Arizona outages", loc="left")
ax = axes[1]
p = fc_pred.sort_values("p90_h").reset_index(drop=True)
groups = np.array_split(np.arange(len(p)), 8)          # 8 equal-size bins of predicted P90
x = [p.p90_h.iloc[g].median() for g in groups]
y = [float(np.mean(p.duration_h.iloc[g] <= p.p90_h.iloc[g])) for g in groups]
ax.plot(x, y, "o-", color=BLUE, ms=3)
ax.axhline(0.9, color=INK2, lw=0.7, ls=":")
ax.set_xscale("log")
ax.set_ylim(0.5, 1.02)
ax.set_xlabel("Predicted P90 (h)")
ax.set_ylabel("Share shorter than P90")
ax.set_title("(b) Coverage, 2023-24", loc="left")
ax.set_xticks([4, 6, 10, 15])
ax.xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
fig.tight_layout(w_pad=0.8)
save(fig, "forecast")

# ---------------------------------------------------------------- Fig: learning inside the shield
fig, axes = plt.subplots(1, 2, figsize=(COL, 1.9))
durs = [12, 24, 48, 72]
xw = np.arange(4)
sh = rlb[(rlb.controller == "shield") & (rlb.warning)].groupby("duration_h").vuln_degree_hours.mean()
pp = rl[rl.controller == "warn"].groupby(["seed", "duration_h"]).vuln_degree_hours.mean().unstack()
rel = (pp / sh - 1) * 100
axes[0].bar(xw, rel.mean().values, yerr=rel.std().values, color=BLUE, width=0.6, error_kw={"lw": 0.8, "capsize": 2})
axes[0].axhline(0, color=INK2, lw=0.6)
axes[0].set_xticks(xw, [f"{d} h" for d in durs])
axes[0].set_ylabel("Change vs fixed pacing (%)")
axes[0].set_title("(a) PPO-Lag., Phoenix, warning", loc="left")
shc = ma[ma.controller == "shield_fixed_pacing"].groupby("duration_h").vuln_degree_hours.mean()
mp = ma[ma.controller == "mappo_shield"].groupby(["seed", "duration_h"]).vuln_degree_hours.mean().unstack()
rel2 = (mp / shc - 1) * 100
axes[1].bar(xw, rel2.mean().values, yerr=rel2.std().values, color=PURPLE, width=0.6, error_kw={"lw": 0.8, "capsize": 2})
axes[1].axhline(0, color=INK2, lw=0.6)
axes[1].set_xticks(xw, [f"{d} h" for d in durs])
axes[1].set_title("(b) MAPPO-Lag., CityLearn", loc="left")
for ax in axes:
    ax.set_xlabel("True outage duration")
fig.tight_layout(w_pad=0.8)
save(fig, "learning")

# ---------------------------------------------------------------- Table: main results
NAMES = [("equal", "Equal curtailment (status quo)"), ("rule", "Rule-based critical-first"),
         ("soft", "Priority as weight, greedy"), ("mpc", "Priority as weight, MPC"),
         ("mpc_hi", "\\quad MPC, critical weight $\\times$100"), ("mpc_p90", "\\quad MPC planned to P90"),
         ("shield", "\\textbf{CareGrid shield}"), ("medical_only", "Medical-only dispatch (bound)"),
         ("oracle", "Perfect-foresight optimum (bound)")]


def cell(df, c, k, d):
    s = df[df.controller == c]
    return tex_num(s[k].mean(), d) if len(s) else "--"


rows = []
for c, name in NAMES:
    rows.append(f"{name} & {cell(main, c, 'crit_device_hours_down', 1)} & {cell(main, c, 'crit_served_pct', 1)} & "
                f"{cell(main, c, 'person_hours_danger', 0)} & {cell(main, c, 'person_degree_hours', 0)} & "
                f"{cell(clm, c, 'crit_device_hours_down', 1)} & {cell(clm, c, 'crit_served_pct', 1)} & "
                f"{cell(clm, c, 'person_hours_danger', 0)} \\\\")
(OUT / "tab_main.tex").write_text(r"""\begin{table*}[t]
\centering
\caption{Outage results without warning, mean over 28 start days $\times$ 4 durations ($n=112$). Device-h: medical device-hours unpowered per outage. Crit.: critical energy served. PH$_{32}$: person-hours indoors above 32.2$^\circ$C. PDH: person-degree-hours above 26.7$^\circ$C. Phoenix uses the full shield (priority tiers, reserve refill, health-twin thermal floor); CityLearn uses the base shield. --: not run on that platform.}
\label{tab:main}
\begin{tabular}{lrrrrrrr}
\toprule
 & \multicolumn{4}{c}{Phoenix community microgrid} & \multicolumn{3}{c}{CityLearn v3, Austin} \\
\cmidrule(lr){2-5}\cmidrule(lr){6-8}
Controller & Device-h & Crit.\ (\%) & PH$_{32}$ & PDH & Device-h & Crit.\ (\%) & PH$_{32}$ \\
\midrule
""" + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n\\end{table*}\n")

# ---------------------------------------------------------------- Table: learning
def r3(d, key, k, dec):
    mu, sd, n = d[key][k]
    return tex_num(mu, dec) + (f" $\\pm$ {tex_num(sd, dec)}" if n > 1 else "")


R = F["rl"]
lines = [r"\multicolumn{4}{l}{\textit{Phoenix, no warning}} \\"]
for key, name in [("soft|nowarn", "Priority as weight"), ("shield|nowarn", "Shield, fixed pacing"),
                  ("nowarn", "Shield + PPO-Lag."), ("nowarn_noshield", "PPO-Lag., no reserve"), ("oracle|nowarn", "Bound")]:
    lines.append(f"{name} & {r3(R, key, 'crit_device_hours_down', 1)} & {r3(R, key, 'person_hours_danger', 0)} & "
                 f"{r3(R, key, 'vuln_degree_hours', 0)} \\\\")
lines.append(r"\midrule \multicolumn{4}{l}{\textit{Phoenix, 24\,h warning}} \\")
for key, name in [("soft|warn", "Priority as weight"), ("shield|warn", "Shield, fixed pacing"),
                  ("fixed_release_0.1|warn", "Shield, best fixed release"), ("warn", "Shield + PPO-Lag."),
                  ("warn_uniform", "\\quad headcount reward"), ("warn_noshield", "PPO-Lag., no reserve"), ("oracle|warn", "Bound")]:
    lines.append(f"{name} & {r3(R, key, 'crit_device_hours_down', 1)} & {r3(R, key, 'person_hours_danger', 0)} & "
                 f"{r3(R, key, 'vuln_degree_hours', 0)} \\\\")
lines.append(r"\midrule \multicolumn{4}{l}{\textit{CityLearn, no warning}} \\")
for key, name in [("soft", "Priority as weight"), ("shield_fixed_pacing", "Shield, fixed pacing"),
                  ("mappo_shield", "Shield + MAPPO-Lag."), ("medical_only", "Medical-only (bound)")]:
    lines.append(f"{name} & {r3(F['mappo'], key, 'crit_device_hours_down', 1)} & "
                 f"{r3(F['mappo'], key, 'person_hours_danger', 0)} & {r3(F['mappo'], key, 'vuln_degree_hours', 0)} \\\\")
(OUT / "tab_learning.tex").write_text(r"""\begin{table}[t]
\centering
\caption{Learning inside the shield on unseen test outages (starts 21--28 July, 12--72\,h, $n=32$). Learned policies: mean $\pm$ s.d.\ over seeds (5 Phoenix, 3 CityLearn). VDH: vulnerability-weighted degree-hours above 26.7$^\circ$C. The perfect-foresight bound minimises unweighted heat exposure, so it bounds medical service and PH$_{32}$-related heat but not VDH.}
\label{tab:learning}
\setlength{\tabcolsep}{2.5pt}
\begin{tabular}{lrrr}
\toprule
Controller & Device-h & PH$_{32}$ & VDH \\
\midrule
""" + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")

# ---------------------------------------------------------------- Table: ablations
pick = [("Shield (no warning, greedy)", "Shield vs.\\ weight (greedy)", "no"),
        ("Shield (warning, learned policy)", "Shield vs.\\ none (PPO-Lag.)$^\\dagger$", "yes"),
        ("Health twin (shield cooling order)", "Health twin vs.\\ building order", "no"),
        ("Health twin (learned-policy reward, warning)", "Twin vs.\\ headcount reward$^\\dagger$", "yes"),
        ("Learned release (warning)", "PPO-Lag.\\ vs.\\ fixed pacing$^\\dagger$", "yes"),
        ("24 h warning (shield)", "Warning vs.\\ none (shield)", "--")]
lines = []
for key, name, warn in pick:
    g = ab[ab.ablation == key]
    if key.startswith("Forecaster"):
        continue
    d = g[g.metric == "Medical device-hours lost"].iloc[0]
    v = g[g.metric == "Vulnerability-weighted degree-h"].iloc[0]
    mark = "$^\\ddagger$" if d.n_outages > 32 else ""
    lines.append(f"{name}{mark} & {warn} & {tex_num(d.diff_B_minus_A, 1)} & {tex_num(v.diff_B_minus_A, 0)} "
                 f"[{tex_num(v.ci_low, 0)}, {tex_num(v.ci_high, 0)}] & {tex_p(v.p)} \\\\")
for lab_part, name in [("forecast P90 only, typical", "Forecast $\\tau_{90}$ vs.\\ 48\\,h"),
                       ("forecast P90 and median, typical", "Forecast $\\tau_{90}$, $\\hat\\tau$ vs.\\ fixed")]:
    g = ab[(ab.ablation == "Forecaster (warning)") & ab.B.str.contains(lab_part, regex=False)]
    d = g[g.metric == "Medical device-hours lost"].iloc[0]
    v = g[g.metric == "Vulnerability-weighted degree-h"].iloc[0]
    lines.append(f"{name}$^\\ddagger$ & yes & {tex_num(d.diff_B_minus_A, 1)} & {tex_num(v.diff_B_minus_A, 0)} "
                 f"[{tex_num(v.ci_low, 0)}, {tex_num(v.ci_high, 0)}] & {tex_p(v.p)} \\\\")
(OUT / "tab_ablations.tex").write_text(r"""\begin{table*}[t]
\centering
\caption{Ablations in Phoenix, one change per row. W: 24\,h warning. $\Delta$: first option minus second (negative favours the first). 95\,\% bootstrap interval for $\Delta$VDH; $p$: Wilcoxon signed-rank test on VDH. Paired over the 32 test outages, or $^\ddagger$all 112 outages. $^\dagger$Learned policies averaged over 5 seeds per outage.}
\label{tab:ablations}
\setlength{\tabcolsep}{6pt}
\begin{tabular}{llrrl}
\toprule
Change & W & $\Delta$Dev.-h & $\Delta$VDH [95\,\% CI] & $p$ \\
\midrule
""" + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n\\end{table*}\n")

# ---------------------------------------------------------------- Table: robustness
LAB = {"pv_forecast_factor": "PV forecast factor $\\alpha$", "sensor_bias_c": "Sensor bias ($^\\circ$C)",
       "battery_kwh": "Battery (kWh)"}
r48 = rob[rob.duration_h == 48].groupby(["factor", "level", "controller"])[["crit_device_hours_down", "person_hours_danger"]].mean()
lines = []
for fct in ("pv_forecast_factor", "sensor_bias_c", "battery_kwh"):
    for lv in sorted(rob[rob.factor == fct].level.unique()):
        s, h = r48.loc[(fct, lv, "soft")], r48.loc[(fct, lv, "shield")]
        lvl = (f"{lv:+g}" if fct == "sensor_bias_c" and lv else f"{lv:g}").replace("-", "$-$")
        lines.append(f"{LAB[fct]} & {lvl} & {tex_num(s.crit_device_hours_down, 1)} & {tex_num(h.crit_device_hours_down, 1)} & "
                     f"{tex_num(s.person_hours_danger, 0)} & {tex_num(h.person_hours_danger, 0)} \\\\")
(OUT / "tab_robust.tex").write_text(r"""\begin{table}[t]
\centering
\caption{Robustness, 48\,h outages, mean over 28 start days, one factor varied at a time.}
\label{tab:robust}
\setlength{\tabcolsep}{3pt}
\begin{tabular}{llrrrr}
\toprule
 & & \multicolumn{2}{c}{Device-h} & \multicolumn{2}{c}{PH$_{32}$} \\
\cmidrule(lr){3-4}\cmidrule(lr){5-6}
Factor & Level & Weight & Shield & Weight & Shield \\
\midrule
""" + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")
print("wrote figures, tables and facts.json")
