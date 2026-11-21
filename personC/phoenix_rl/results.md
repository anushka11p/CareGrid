# Step 5: Phoenix PPO-Lagrangian inside the shield

Trained on outages starting 1-20 July 2023, tested on unseen outages starting 21-28 July (12/24/48/72 h, n = 32). Learned rows: mean ± s.d. over seeds of the per-seed test means.


## No warning (battery as found)

| controller                  |   seeds | Device-h lost   | Person-h > 32.2 C   | Vuln.-weighted degree-h   |
|:----------------------------|--------:|:----------------|:--------------------|:--------------------------|
| Priority as weight (greedy) |       1 | 105.0           | 438.6               | 7,058.3                   |
| Shield, fixed pacing        |       1 | 0.0             | 469.0               | 7,241.8                   |
| Shield + MPC                |       1 | 0.0             | 469.0               | 7,241.8                   |
| Shield, fixed release 0.02  |       1 | 0.0             | 468.3               | 7,242.8                   |
| Shield, fixed release 0.05  |       1 | 0.0             | 468.4               | 7,242.1                   |
| Shield, fixed release 0.1   |       1 | 0.0             | 468.6               | 7,242.0                   |
| Shield, fixed release 0.3   |       1 | 0.0             | 468.6               | 7,241.2                   |
| Shield, fixed release 1.0   |       1 | 0.0             | 469.0               | 7,243.2                   |
| Shield + PPO-Lag.           |       5 | 0.0 ± 0.0       | 468.9 ± 0.4         | 7,242.0 ± 0.6             |
| PPO-Lag. without reserve    |       5 | 172.7 ± 20.7    | 434.2 ± 1.9         | 6,606.1 ± 31.3            |
| Best possible (oracle)      |       1 | 0.0             | 353.9               | 7,106.5                   |

## 24 h warning (battery pre-charged)

| controller                          |   seeds | Device-h lost   | Person-h > 32.2 C   | Vuln.-weighted degree-h   |
|:------------------------------------|--------:|:----------------|:--------------------|:--------------------------|
| Priority as weight (greedy)         |       1 | 87.6            | 372.7               | 6,299.4                   |
| Shield, fixed pacing                |       1 | 0.0             | 388.5               | 6,297.7                   |
| Shield + MPC                        |       1 | 0.0             | 387.8               | 6,278.9                   |
| Shield, fixed release 0.02          |       1 | 0.0             | 422.8               | 6,454.0                   |
| Shield, fixed release 0.05          |       1 | 0.0             | 394.8               | 6,291.4                   |
| Shield, fixed release 0.1           |       1 | 0.0             | 388.6               | 6,217.1                   |
| Shield, fixed release 0.3           |       1 | 0.0             | 411.8               | 6,341.2                   |
| Shield, fixed release 1.0           |       1 | 0.0             | 432.3               | 6,543.7                   |
| Shield + PPO-Lag.                   |       5 | 0.0 ± 0.0       | 388.5 ± 7.8         | 6,144.8 ± 57.8            |
| Shield + PPO-Lag., headcount reward |       5 | 0.0 ± 0.0       | 389.2 ± 8.9         | 6,153.4 ± 65.5            |
| PPO-Lag. without reserve            |       5 | 146.9 ± 34.0    | 363.5 ± 16.3        | 5,710.6 ± 145.8           |
| Best possible (oracle)              |       1 | 0.0             | 285.2               | 5,845.7                   |

## Vulnerability-weighted degree-hours by outage length

|                                   |   12 |   24 |   48 |    72 |
|:----------------------------------|-----:|-----:|-----:|------:|
| shield, fixed pacing (no warning) | 1448 | 4005 | 9110 | 14404 |
| shield, fixed pacing (warning)    | 1105 | 3123 | 7851 | 13112 |
| nowarn                            | 1448 | 4004 | 9111 | 14405 |
| nowarn_noshield                   | 1087 | 3475 | 8471 | 13392 |
| warn                              |  857 | 2881 | 7783 | 13058 |
| warn_noshield                     |  632 | 2551 | 7376 | 12283 |
| warn_uniform                      |  849 | 2888 | 7800 | 13076 |

## End of training (mean over seeds)

| config          |   mean_cost |   cost_limit |   lambda |
|:----------------|------------:|-------------:|---------:|
| nowarn          |       10.84 |         8.68 |     9.83 |
| nowarn_noshield |        9.91 |         7.96 |     8.64 |
| warn            |        8.82 |         6.99 |     8.51 |
| warn_noshield   |        7.74 |         6.63 |     4.91 |
| warn_uniform    |        8.83 |         6.99 |     8.56 |
