# Step 1: reserve-refill fix (outage energy accounting)

## The bug
`caregrid/sim.py`, `_shield_budget()`. The shield computes `deficit_kwh`, how far stored energy is below the
medical reserve, but the next line was `pv_left = max(0.0, pv_left)`, so the deficit was never used. Surplus
solar went to cooling even when the battery could not carry the medical devices through the night.

## The fix
```python
pv_left = max(0.0, pv_left - min(deficit_kwh / ctx["eta"] ** 2, ctx["batt_kw"]))
```
Surplus solar first refills the battery up to the reserve (dividing by eta^2 converts deliverable energy back to
the solar needed to store it, capped at the battery's charge power). `demo/engine.js` already had this line.

The JavaScript demo engine also cooled toward 32.2 C while the Python cools toward 26.7 C (Person A's final
choice; see `caregrid/sim_before_caution_target.py`). The JS now matches the Python.

## Validation
All 28 outage starts (1-28 July, 14:00) x 4 durations, no warning (`before.csv`, `after.csv`):

Medical device-hours unpowered per outage (mean of 28):

|                    |   before |   after |
|:-------------------|---------:|--------:|
| ('mpc_shield', 12) |      0   |     0   |
| ('mpc_shield', 24) |      0   |     0   |
| ('mpc_shield', 48) |     76.2 |     0.1 |
| ('mpc_shield', 72) |    192.5 |     0.1 |
| ('shield', 12)     |      0   |     0   |
| ('shield', 24)     |      0   |     0   |
| ('shield', 48)     |    105.8 |     0.1 |
| ('shield', 72)     |    222.1 |     0.1 |
| ('soft', 12)       |      0   |     0   |
| ('soft', 24)       |     22.2 |    22.2 |
| ('soft', 48)       |    138.4 |   138.4 |
| ('soft', 72)       |    254.6 |   254.6 |

Person-hours above 32.2 C per outage (mean of 112):

| controller   |   before |   after |
|:-------------|---------:|--------:|
| mpc_shield   |      415 |     429 |
| shield       |      415 |     429 |
| soft         |      409 |     409 |

- Before the fix the shield was barely better than weighted priority (`soft`) on long outages.
- After the fix it loses 0.1 device-hours on 48 and 72 h outages. `soft` is unchanged because it does not use the shield.
- The cost is a few more person-hours in dangerous heat, because energy that cooled homes now protects medical devices.
- `tests/test_parity.py`: before the fix it failed (Python and JS disagreed on medical service); after both changes it passes on 128 scenarios (max abs difference 3.6e-12).

## What this changes for Persons A and B
Every shielded result produced with the old line is affected: Person A's outage, battery, PV-forecast and
sensor-bias results for `shield` and `mpc_shield`, and `results/scenarios.csv` rows for shielded controllers.
For example Person A's 72 h MPC-shield result goes from about 198 device-hours to about 0.1. Step 8 regenerates all of them.
