# Step 2: baselines, verified and documented

All controllers live in `caregrid/sim.py` (greedy and rule-based) and `caregrid/oracle.py` (linear programs).
Every controller sees the same inputs each hour: solar, battery state, indoor temperatures and the utility's
restoration estimate (24 h). Only the oracle knows the true outage length.

| Controller | Code | What it does |
|---|---|---|
| `equal` | `ctrl_equal` | Status quo. Scales every load by the same fraction when supply is short; a medical device getting less than full power trips. Spends the battery as fast as loads ask. |
| `rule` | `ctrl_rule` | Industry heuristic. Serves medical devices, then essential circuits; runs AC from the battery only while it is above 40 %, otherwise only from solar. |
| `soft` | `ctrl_soft` | Priority as a weight. Ranks loads by value per kWh (medical 10, essential 2, cooling = heat weight x heat risk) and paces the battery evenly to the restoration estimate. Medical service can lose to cooling. |
| `mpc` | `mpc_decision` | Receding-horizon linear program, re-solved every hour to the restoration estimate (at least 12 h) with perfect weather and solar forecasts; medical weight 10. |
| `mpc_hi` | same | As `mpc` with medical weight 1000. |
| `mpc_p90` | same | As `mpc_hi` but plans to the worst-case restoration time (48 h) instead of the estimate. |
| `shield` | `ctrl_shield` | CareGrid. Medical devices by tier P1-P3, battery reserve to the worst case, solar refills the reserve, thermal-safety cooling, then essential and discretionary loads. |
| `mpc_shield`, `mpc_p90_shield` | `apply_shield` | MPC proposals passed through the shield. |
| `oracle` | `run_oracle` | Best possible. One linear program over the whole outage that knows the true length and lets devices run at fractions; a lower bound no real controller can reach. |

## Case study: 19 July 14:00, 48 h

| controller     |   crit_device_hours_down |   crit_served_pct |   person_hours_danger |   person_degree_hours |   max_tin |
|:---------------|-------------------------:|------------------:|----------------------:|----------------------:|----------:|
| equal          |                      463 |               2   |                   697 |                6411.3 |      38.5 |
| rule           |                      191 |              61.4 |                   714 |                7184.6 |      39.4 |
| soft           |                      139 |              71.7 |                   576 |                6077.9 |      42.2 |
| shield         |                        0 |             100   |                   602 |                6765.7 |      43.3 |
| mpc            |                        0 |             100   |                   488 |                5725.6 |      43.4 |
| mpc_hi         |                        0 |             100   |                   488 |                5725.6 |      43.4 |
| mpc_p90        |                        0 |             100   |                   450 |                5663.1 |      43.4 |
| mpc_shield     |                        0 |             100   |                   602 |                6765.7 |      43.3 |
| mpc_p90_shield |                        0 |             100   |                   602 |                6765.7 |      43.3 |
| oracle         |                        0 |             100   |                   456 |                5664.4 |      43.4 |

## Means over 28 outage starts x 48 and 72 h (no warning)

| controller     |   crit_device_hours_down |   crit_served_pct |   person_hours_danger |   person_degree_hours |   ess_kwh_unserved |
|:---------------|-------------------------:|------------------:|----------------------:|----------------------:|-------------------:|
| equal          |                    580   |               1.8 |                 750.2 |                6921.2 |              195   |
| rule           |                    247.5 |              60.1 |                 841.7 |                7917.9 |              111.8 |
| soft           |                    196.5 |              68.7 |                 665.1 |                6663.4 |              205.1 |
| mpc            |                      1.5 |              99.8 |                 560.7 |                6131.6 |              252   |
| mpc_hi         |                      1.6 |              99.8 |                 560.7 |                6131.3 |              252   |
| mpc_p90        |                      0.6 |              99.9 |                 532.9 |                6020.2 |              252   |
| shield         |                      0.1 |             100   |                 690.4 |                7308.8 |              252   |
| mpc_shield     |                      0.1 |             100   |                 690.4 |                7308.8 |              252   |
| mpc_p90_shield |                      0.1 |             100   |                 690.4 |                7308.8 |              252   |
| oracle         |                      0   |             100   |                 521.5 |                5976   |              239.9 |

## Sanity checks

| check                                                                                            | passed   |
|:-------------------------------------------------------------------------------------------------|:---------|
| Oracle loses no more medical service than any controller, every outage                           | True     |
| Oracle has the best heat + essential-load score among controllers that keep every device powered | True     |
| MPC planned to P90 loses no more medical service than MPC planned to the estimate (mean)         | True     |
| Equal curtailment has the most medical device-hours lost (mean)                                  | True     |
| Every shielded controller loses at most 0.5 device-hours per outage (mean)                       | True     |

The second check was first written as "the oracle has the least heat". It failed on 20 of 51 outages, by at most
0.22 %, always against `mpc_p90`. The oracle does not minimise heat alone: after medical service it minimises
heat plus 2 x essential energy unserved. On the case study `mpc_p90` had 5,663 person-degree-hours and
202 kWh of essential load unserved (score 6,066); the oracle had 5,664 and 189 (score 6,042). The check now
compares that score, and passes.

## Finding for the paper
`shield`, `mpc_shield` and `mpc_p90_shield` give identical heat results on 100 % of outages. Person A's
`apply_shield` sets cooling itself (thermal-safety floor) and uses the MPC proposal only for essential and
discretionary loads, so the MPC's cooling plan is discarded. Either report the three as one controller, or change
`apply_shield` to keep the MPC's cooling where the budget allows.
