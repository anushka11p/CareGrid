"""Step 3: does ordering thermal-safety cooling by the health twin help?

Shield on all 28 start days x 12/24/48/72 h (no warning), cooling ordered by health twin vs by
building index. Paired Wilcoxon signed-rank test per metric. Writes ablation.csv and results.md."""
import itertools
import pathlib
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import caregrid.sim as S  # noqa: E402
from caregrid.health_twin import RESIDENTS, vulnerability  # noqa: E402

INP, A, BLDS = S.load_inputs(), S.Assets(), S.community()
STATES, _ = S.run_normal(INP, A, BLDS)
METRICS = ["vuln_degree_hours", "person_degree_hours", "person_hours_danger", "crit_device_hours_down"]


def run(job):
    order, day, dur = job
    S.THERMAL_ORDER = order
    start = 24 * day + 14
    soc0, tin0 = STATES[start]
    m = S.metrics(S.run_outage(INP, A, BLDS, start, dur, "shield", soc0, tin0), BLDS)
    return {"order": order, "day": day, "duration_h": dur, **m}


if __name__ == "__main__":
    out = ROOT / "personC" / "step3"
    jobs = list(itertools.product(["index", "health_twin"], range(1, 29), (12, 24, 48, 72)))
    with Pool(6) as p:
        df = pd.DataFrame(p.map(run, jobs, chunksize=4))
    df.to_csv(out / "ablation.csv", index=False)
    a = df[df.order == "index"].set_index(["day", "duration_h"]).sort_index()
    b = df[df.order == "health_twin"].set_index(["day", "duration_h"]).sort_index()
    rows = []
    for k in METRICS:
        diff = b[k] - a[k]
        p = wilcoxon(a[k], b[k]).pvalue if np.any(diff != 0) else 1.0
        rows.append({"metric": k, "building order": round(a[k].mean(), 1), "health twin": round(b[k].mean(), 1),
                     "change %": round(100 * (b[k].mean() / a[k].mean() - 1), 1) if a[k].mean() else 0.0,
                     "outages better / worse": f"{(diff < -1e-9).sum()} / {(diff > 1e-9).sum()}", "p": f"{p:.2g}"})
    res = pd.DataFrame(rows)
    scores = pd.DataFrame([{"home": h, "residents": len(r), "ages": ", ".join(str(x.age) for x in r),
                            "conditions": "; ".join(", ".join(x.conditions) or "none" for x in r),
                            "vulnerability": round(vulnerability(h), 2)} for h, r in RESIDENTS.items()])
    (out / "results.md").write_text("# Step 3: health twin\n\n## Scores\n\n" + scores.to_markdown(index=False)
                                    + "\n\n## Ablation (shield, 112 outages, paired)\n\n" + res.to_markdown(index=False) + "\n")
    print(scores.to_string(index=False)); print(); print(res.to_string(index=False))
