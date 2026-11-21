# Step 6: MAPPO-Lagrangian on CityLearn v3 (10 Austin homes)

One shared actor per home on local observations, centralised reward and cost critics on all homes. Trained on outages starting 1-20 July 2018, tested on unseen starts 21-28 July (12/24/48/72 h, n = 32), no warning. Learned rows: mean ± s.d. over seeds.

| controller                         |   seeds | Device-h lost   | Person-h > 32.2 C   | Vuln.-weighted degree-h   | Essential kWh unserved   | Unplanned import kWh   |
|:-----------------------------------|--------:|:----------------|:--------------------|:--------------------------|:-------------------------|:-----------------------|
| Priority as weight (greedy)        |       1 | 94.0            | 61.8                | 2,062.0                   | 49.5                     | 0.0                    |
| Shield (greedy, citylearn_port)    |       1 | 3.4             | 80.0                | 2,496.6                   | 58.7                     | 0.0                    |
| Shield, fixed pacing (policy path) |       1 | 3.4             | 80.0                | 2,496.6                   | 58.7                     | 0.0                    |
| Shield + MAPPO-Lag.                |       3 | 1.3 ± 0.1       | 82.2 ± 0.9          | 2,616.7 ± 34.8            | 52.4 ± 1.5               | 0.0 ± 0.0              |
| Medical-only dispatch (bound)      |       1 | 0.0             | 405.1               | 6,799.8                   | 136.5                    | 0.0                    |

The two shield rows must agree: the fixed-pacing release through the MAPPO code path reproduces citylearn_port's greedy shield.

## MAPPO vs fixed pacing (paired over test outages, seeds averaged)

| metric                  |   fixed pacing |   MAPPO |   change % |       p |
|:------------------------|---------------:|--------:|-----------:|--------:|
| Device-h lost           |            3.4 |     1.3 |      -61.8 | 0.00042 |
| Person-h > 32.2 C       |           80   |    82.2 |        2.7 | 0.51    |
| Vuln.-weighted degree-h |         2496.6 |  2616.7 |        4.8 | 0.016   |
| Essential kWh unserved  |           58.7 |    52.4 |      -10.7 | 0.0011  |

## Vulnerability-weighted degree-hours by outage length

| controller          |   12 |   24 |   48 |   72 |
|:--------------------|-----:|-----:|-----:|-----:|
| mappo_shield        |  884 | 1479 | 3083 | 5020 |
| shield_fixed_pacing |  921 | 1518 | 2883 | 4664 |
| soft                |  665 | 1206 | 2440 | 3937 |

## End of training

|   seed |   episodes |   mean_cost |   cost_limit |   lambda |   mean_release |   minutes |
|-------:|-----------:|------------:|-------------:|---------:|---------------:|----------:|
|      1 |        320 |        0.59 |         0.71 |     0.25 |           0.11 |      6.77 |
|      0 |        320 |        0.95 |         0.72 |     0.23 |           0.09 |      6.99 |
|      2 |        320 |        0.76 |         0.57 |     0.45 |           0.08 |      6.72 |
