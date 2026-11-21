"""Step 4: outage-duration forecaster from EAGLE-I (ORNL), Arizona, 2015-2024.

Data: Brelsford et al., "A dataset of recorded electricity outages by United States county
2014-2022", Scientific Data 11, 271 (2024); Figshare 10.6084/m9.figshare.24237376. Rows are
county x 15-minute customers-out counts; zero rows are not recorded.

Events: per county, a run of 15-minute records with at least MIN_OUT customers out, gaps of up
to 30 min merged (a missed scrape does not split an outage), keeping events that peak at
PEAK_MIN or more customers. Duration = first to last record at or above MIN_OUT, + 15 min.

Model: gradient-boosted quantile regression of log duration on what a utility knows at the
first hour of an outage: month, hour and weekday of onset, customers out in the first hour,
county size. Train 2015-2021, test on unseen years 2023-2024 (2022 held for checking).
Baseline: the training set's unconditional quantiles.

Writes personC/forecast/{events.csv, test_predictions.csv, results.md, tau90.json}.
"""
import json
import pathlib
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "eaglei"
OUT = pathlib.Path(__file__).resolve().parent
MIN_OUT, PEAK_MIN = 100, 1000
FEATURES = ["month", "hour", "weekday", "log_first_hour_out", "log_county_customers", "summer"]
TRAIN_YEARS, CHECK_YEARS, TEST_YEARS = range(2015, 2022), [2022], [2023, 2024]
MARICOPA = 4013


def events_from_year(path):
    d = pd.read_csv(path, dtype={"fips_code": int})
    d["t"] = pd.to_datetime(d.run_start_time)
    d = d[d.customers_out >= MIN_OUT].sort_values(["fips_code", "t"])
    out = []
    for fips, g in d.groupby("fips_code"):
        t = g.t.to_numpy()
        new = np.r_[True, np.diff(t) > np.timedelta64(30, "m")]
        ev = np.cumsum(new)
        for _, e in g.assign(ev=ev).groupby("ev"):
            if e.customers_out.max() < PEAK_MIN:
                continue
            start = e.t.iloc[0]
            first_hour = e[e.t < start + pd.Timedelta(hours=1)].customers_out.max()
            out.append({"fips": fips, "county": e.county.iloc[0], "start": start,
                        "duration_h": (e.t.iloc[-1] - start) / pd.Timedelta(hours=1) + 0.25,
                        "peak_out": int(e.customers_out.max()), "first_hour_out": int(first_hour)})
    return out


def build_events():
    mcc = pd.read_csv(RAW / "MCC.csv", encoding="utf-8-sig").rename(columns={"County_FIPS": "fips", "Customers": "county_customers"})
    mcc["fips"] = pd.to_numeric(mcc.fips, errors="coerce")
    mcc = mcc.dropna(subset=["fips"]).astype({"fips": int})
    rows = []
    for f in sorted(RAW.glob("az_*.csv")):
        rows += events_from_year(f)
    ev = pd.DataFrame(rows).merge(mcc, on="fips", how="left")
    ev["year"] = ev.start.dt.year
    ev["month"] = ev.start.dt.month
    ev["hour"] = ev.start.dt.hour
    ev["weekday"] = (ev.start.dt.day_of_week < 5).astype(int)
    ev["summer"] = ev.month.isin([6, 7, 8, 9]).astype(int)
    ev["log_first_hour_out"] = np.log10(ev.first_hour_out)
    ev["log_county_customers"] = np.log10(ev.county_customers.fillna(ev.county_customers.median()))
    return ev


def pinball(y, q, a):
    d = y - q
    return float(np.mean(np.maximum(a * d, (a - 1) * d)))


def main():
    ev = build_events()
    ev.to_csv(OUT / "events.csv", index=False)
    years = sorted(ev.year.unique())
    tr, te = ev[ev.year.isin(TRAIN_YEARS)], ev[ev.year.isin(TEST_YEARS)]
    if te.empty:                                   # partial download: hold out the last year
        tr, te = ev[ev.year < years[-1]], ev[ev.year == years[-1]]
    y_tr, y_te = np.log(tr.duration_h), np.log(te.duration_h)
    res, preds = {}, te[["fips", "county", "start", "duration_h", "first_hour_out"] + FEATURES].copy()
    for a in (0.5, 0.9):
        m = GradientBoostingRegressor(loss="quantile", alpha=a, n_estimators=300, max_depth=3,
                                      learning_rate=0.05, min_samples_leaf=20, random_state=0)
        m.fit(tr[FEATURES], y_tr)
        q = m.predict(te[FEATURES])
        base = np.quantile(y_tr, a)
        preds[f"p{int(a * 100)}_h"] = np.exp(q)
        res[a] = {"model_pinball": pinball(y_te, q, a), "baseline_pinball": pinball(y_te, base, a),
                  "coverage": float(np.mean(y_te <= q)), "baseline_coverage": float(np.mean(y_te <= base)),
                  "baseline_h": float(np.exp(base)), "model": m}
    preds.to_csv(OUT / "test_predictions.csv", index=False)

    # Forecasts for the simulated scenario: a July weekday outage in Maricopa starting at 14:00.
    # "typical" uses the median first-hour size of past summer-afternoon Maricopa events,
    # "large" the 90th percentile of that size.
    past = tr[(tr.fips == MARICOPA) & (tr.summer == 1) & tr.hour.between(12, 18)]
    if past.empty:
        past = tr
    mar = ev[ev.fips == MARICOPA].county_customers.dropna()
    county = float(mar.iloc[0]) if len(mar) else 1.74e6
    scen = {}
    for key, q in (("typical", 0.5), ("large", 0.9)):
        size = float(past.first_hour_out.quantile(q))
        x = pd.DataFrame([{"month": 7, "hour": 14, "weekday": 1, "log_first_hour_out": np.log10(size),
                           "log_county_customers": np.log10(county), "summer": 1}])
        scen[key] = {"first_hour_out": size,
                     "tau50_h": float(np.exp(res[0.5]["model"].predict(x[FEATURES])[0])),
                     "tau90_h": float(np.exp(res[0.9]["model"].predict(x[FEATURES])[0]))}
    json.dump({**scen, "train_years": [int(y) for y in sorted(tr.year.unique())],
               "test_years": [int(y) for y in sorted(te.year.unique())], "n_past_maricopa_summer_afternoon": int(len(past))},
              open(OUT / "tau90.json", "w"), indent=1)

    desc = ev.groupby("year").agg(events=("duration_h", "size"), median_h=("duration_h", "median"),
                                  p90_h=("duration_h", lambda s: s.quantile(0.9)), max_h=("duration_h", "max"))
    tab = pd.DataFrame([{"quantile": f"P{int(a * 100)}", "coverage (target)": f"{r['coverage']:.2f} ({a})",
                         "baseline coverage": f"{r['baseline_coverage']:.2f}", "pinball loss": round(r["model_pinball"], 3),
                         "baseline pinball": round(r["baseline_pinball"], 3),
                         "improvement %": round(100 * (1 - r["model_pinball"] / r["baseline_pinball"]), 1)}
                        for a, r in res.items()])
    md = (f"# Step 4: outage-duration forecaster (EAGLE-I, Arizona)\n\n"
          f"Events: >= {MIN_OUT} customers out, peak >= {PEAK_MIN}, gaps <= 30 min merged. "
          f"Train {sorted(tr.year.unique())}, test {sorted(te.year.unique())} "
          f"({len(tr)} / {len(te)} events).\n\n## Events per year\n\n" + desc.round(1).to_markdown()
          + "\n\n## Test-set quality (log duration)\n\n" + tab.to_markdown(index=False)
          + f"\n\nCoverage = share of test outages shorter than the predicted quantile.\n\n"
          f"## Forecasts for the simulated scenario\n\nJuly, Maricopa County, onset 14:00 on a weekday "
          f"({len(past)} past summer-afternoon Maricopa events):\n\n"
          + "\n".join(f"- {k}: {v['first_hour_out']:,.0f} customers out in the first hour -> median restoration "
                       f"**{v['tau50_h']:.1f} h**, P90 **{v['tau90_h']:.1f} h**" for k, v in scen.items()) + "\n")
    (OUT / "results.md").write_text(md)
    print(md)


if __name__ == "__main__":
    sys.exit(main())
