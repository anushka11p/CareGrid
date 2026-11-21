"""Step 5 report: tables and figures from personC/phoenix_rl/results/*.csv."""
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
RES = HERE / "results"
K = {"crit_device_hours_down": "Device-h lost", "person_hours_danger": "Person-h > 32.2 C",
     "vuln_degree_hours": "Vuln.-weighted degree-h"}
NAMES = {"soft": "Priority as weight (greedy)", "shield": "Shield, fixed pacing", "mpc_shield": "Shield + MPC",
         "nowarn": "Shield + PPO-Lag.", "warn": "Shield + PPO-Lag.", "warn_uniform": "Shield + PPO-Lag., headcount reward",
         "nowarn_noshield": "PPO-Lag. without reserve", "warn_noshield": "PPO-Lag. without reserve",
         "oracle": "Best possible (oracle)"}


def table(ev, base, warning):
    rows = []
    b = base[base.warning == warning]
    for c in ("soft", "shield", "mpc_shield") + tuple(sorted(x for x in b.controller.unique() if x.startswith("fixed_release"))):
        g = b[b.controller == c]
        rows.append({"controller": NAMES.get(c, c.replace("fixed_release_", "Shield, fixed release ")), "seeds": 1,
                     **{v: f"{g[k].mean():,.1f}" for k, v in K.items()}})
    configs = ["warn", "warn_uniform", "warn_noshield"] if warning else ["nowarn", "nowarn_noshield"]
    for c in configs:
        ps = ev[ev.controller == c].groupby("seed")[list(K)].mean()
        rows.append({"controller": NAMES[c], "seeds": len(ps),
                     **{v: f"{ps[k].mean():,.1f} ± {ps[k].std():,.1f}" for k, v in K.items()}})
    g = b[b.controller == "oracle"]
    rows.append({"controller": NAMES["oracle"], "seeds": 1, **{v: f"{g[k].mean():,.1f}" for k, v in K.items()}})
    return pd.DataFrame(rows)


def main():
    ev, base = pd.read_csv(RES / "eval.csv"), pd.read_csv(RES / "baselines.csv")
    tr = pd.read_csv(RES / "training.csv")
    md = ["# Step 5: Phoenix PPO-Lagrangian inside the shield\n",
          "Trained on outages starting 1-20 July 2023, tested on unseen outages starting 21-28 July "
          "(12/24/48/72 h, n = 32). Learned rows: mean ± s.d. over seeds of the per-seed test means.\n"]
    for w in (False, True):
        md.append(f"\n## {'24 h warning (battery pre-charged)' if w else 'No warning (battery as found)'}\n")
        md.append(table(ev, base, w).to_markdown(index=False))
    by = ev.groupby(["controller", "duration_h"]).vuln_degree_hours.mean().unstack()
    sh = base[(base.controller == "shield")].groupby(["warning", "duration_h"]).vuln_degree_hours.mean().unstack()
    md.append("\n## Vulnerability-weighted degree-hours by outage length\n")
    md.append(pd.concat([sh.rename(index={False: "shield, fixed pacing (no warning)", True: "shield, fixed pacing (warning)"}),
                         by]).round(0).to_markdown())
    fin = tr.sort_values("steps").groupby(["config", "seed"]).tail(1).groupby("config")[["mean_cost", "cost_limit", "lambda"]].mean()
    md.append("\n## End of training (mean over seeds)\n\n" + fin.round(2).to_markdown())
    (HERE / "results.md").write_text("\n".join(md) + "\n")

    fig, axes = plt.subplots(2, 1, figsize=(6, 4.6), sharex=True)
    for c, col in (("warn", "#2a78d6"), ("warn_uniform", "#1baf7a"), ("warn_noshield", "#eb6834"), ("nowarn", "#8a8984")):
        g = tr[tr.config == c].groupby("steps")
        for ax, k in zip(axes, ("mean_cost", "lambda")):
            m, s = g[k].mean(), g[k].std()
            ax.plot(m.index / 1e3, m.values, color=col, lw=1.3, label=NAMES[c] + (" (warning)" if c.startswith("warn") else " (no warning)"))
            ax.fill_between(m.index / 1e3, m - s, m + s, color=col, alpha=0.15, lw=0)
    axes[0].set_ylabel("Person-h > 32.2 C per hour")
    axes[1].set_ylabel("Lagrange multiplier")
    axes[1].set_xlabel("Training steps (thousands)")
    axes[0].legend(frameon=False, fontsize=7)
    for ax in axes:
        ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(HERE / "training_curves.png", dpi=200)
    print("\n".join(md))


if __name__ == "__main__":
    main()
