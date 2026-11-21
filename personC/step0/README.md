# Step 0: reproduction of the handover

| Check | Result |
|---|---|
| 80 random rows of `results/scenarios.csv` re-run with `experiments/run_pilot.run_one` (60 greedy/rule controllers, 20 MPC/oracle) | All match, max abs difference 1.4e-12 (`reproduce_sample.csv`) |
| Person B `evaluate_two_constraint.py`, fixed-allocation baselines | Match the stored CSV exactly |
| Person B trained PPO-Lagrangian (`models/two_constraint_10k`) | Close but not identical: reward 754.49 vs stored 756.93, thermal cost 391.16 vs 389.99 (`personB_rerun.csv`). Most likely the stored row came from another checkpoint or PyTorch nondeterminism. |

Issues found while reproducing (handled in later steps):
1. `caregrid/sim.py` line 323 discards the reserve deficit, so solar never refills the medical reserve (Step 1).
2. Person B's `PhoenixRLEnv` sets `reserve_kwh = 0.0`, so the shield's reserve is never active in RL training (Step 5).
3. Person B's environment sets `forecast_end = start + duration`, so the agent knows the true outage length (Step 5).
4. Person B trains and evaluates on the same single outage (start index 300/500, 24 h), one seed (Step 5).
