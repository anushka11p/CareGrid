# Preliminary Results (draft for the CareGrid proposal)

## Pilot setup

We built a reproducible pilot simulator to test CareGrid's central design choice: protecting
older adults' electricity-dependent medical equipment as a **hard constraint enforced by a
runtime shield**, instead of as a high weight in the controller's objective. The pilot
community has eight elderly households and a six-resident care facility. Between them they run
12 critical devices: five oxygen concentrators, a ventilator, two CPAP machines, three
medication fridges and a power-wheelchair charger. The buildings share a 60 kWp PV array and a
150 kWh community battery.

All environmental inputs are real. We used hourly Phoenix, AZ weather for July 2023, the city's
hottest month on record, with a peak of 46.8 °C (Open-Meteo / ERA5). Household base-load
shapes come from NREL ResStock (Maricopa County). Each building is a grey-box 1R1C thermal
model. Calibrated against ResStock, it uses 55.9 kWh/day of July cooling, against 51.1 kWh/day
for the cooler July 2018. Without cooling, indoor temperature reaches about 39.5 °C within
eight hours on the hottest day.

The grid fails at 14:00 on each of 28 days in July. The true outage lasts 12, 24, 48 or 72 h,
but every controller is told restoration will take 24 h. We ran each case with and without a
24 h warning, plus sweeps over battery size, heat weighting, the shield's worst-case bound and
the outage start time: 6,048 simulated outages in total. We compared ten controllers:

- equal curtailment (status quo) and a rule-based critical-first heuristic
- greedy and model-predictive (MPC) controllers that treat medical priority as a weight
- the same policies wrapped in the CareGrid shield
- a perfect-foresight linear-programming bound

## Findings

1. **The shield eliminated medical-device outages.** Pooled over 112 outages with no warning,
   the weighted greedy controller left medical devices unpowered for 104 device-hours per
   outage (95% CI 85–122) and served 82.0% of critical energy. The same controller inside the
   shield lost 0 device-hours and served 100% (paired Wilcoxon p = 1.6 × 10⁻¹⁵). Under status-quo
   equal curtailment, 374 device-hours were lost and only 4.2% of critical energy was served.
2. **Priority-as-weight is safe only inside a narrow weight band.** An MPC planner with a
   perfect 12 h-plus weather forecast was nearly safe at its default weights (0.8
   device-hours lost per 48 h outage). Doubling the weight on cooling raised that to 386
   device-hours, and at four times the weight it reached 472. Raising the medical weight 100×
   did not remove the residual failures (p = 0.33). Outages starting at 20:00 cost the
   unshielded MPC 39 device-hours. The shielded planner lost 0 device-hours at every weight,
   start time and battery size tested.
3. **The guarantee has a measurable cost.** The shield's battery reserve increased resident
   heat exposure (person-degree-hours above 26.7 °C) by about 6% relative to the same
   unshielded policy (4,073 → 4,324 for greedy; 3,727 → 3,974 for MPC). The best shielded
   controller (shield + worst-case-horizon MPC) came within 8% of the perfect-foresight bound
   on heat exposure while losing no device-hours. That gap is what the proposed constrained
   multi-agent RL policy should close.
4. **Outage warnings matter.** A 24 h warning that pre-charges the battery (30% → 100% state
   of charge, about 111 kWh extra grid energy per event) cut heat exposure by 11–19% across
   controllers. This supports the Predictive Shield component.

## Replication on CityLearn v3

To check that the result does not depend on our own building model, we re-ran the
experiment on CityLearn v3.0.2 using its built-in `tx_travis_county_neighborhood` dataset.
That dataset provides real NREL ResStock homes in Austin, TX, measured 2018 weather from the
Camp Mabry station, and per-home LSTM indoor-temperature models trained on EnergyPlus output.
Ten homes were assigned the same elderly households and medical devices as before. Each home
islands on its own 6 kW PV array (output from NREL PVWatts v8) and a 13.5 kWh / 5 kW battery.
Outages start at 14:00 on each of 1–28 July 2018 and last 12, 24, 48 or 72 h, with the
utility estimate again fixed at 24 h. We ran 2,016 episodes.

- **Medical outages fell by 92%.** The weighted controller left medical devices unpowered for
  81.4 device-hours per outage (95% CI 66.7–96.4). The shielded controller left them unpowered
  for 6.1 (4.1–8.4), serving 98.3% of critical energy against 81.4% (Wilcoxon p = 8.5 × 10⁻¹⁹).
  Status-quo equal curtailment lost 209 device-hours.
- **The shield is close to, but not at, the physical limit.** A medical-only reference
  dispatch, which spends energy on nothing but medical devices, lost 2.2 device-hours. The
  shield matched it within 4 device-hours up to 48 h. At 72 h, past the shield's 48 h
  worst-case bound, it lost 14.9 against the reference's 2.9.
- **The heat cost is larger with per-home batteries.** Residents spent 44 person-hours indoors
  above 32.2 °C per outage under the shield, against 32 under the weighted controller
  (+13 person-hours, p = 8.7 × 10⁻¹⁹), and 13.5 kWh is a small battery for a 48 h reserve.
  Medical-only dispatch shows the extreme of that trade-off: 340 person-hours.
- **On this platform the heat weight barely mattered.** CityLearn always serves base load
  before cooling within an hour, so the weighted controller's failures come from spending the
  battery on cooling early, not from the within-hour ranking. Its device-hours lost stayed at
  104–106 across heat weights from 0.25 to 8, while the shield stayed at 6.3–6.5.

Methods note: in CityLearn 3.0.2's built-in outage mode, batteries cannot discharge. The
discharge cap uses a local-load estimate taken before loads are energised and net of PV, so it
is zero. We therefore ran CityLearn grid-connected and enforced islanding in the controller
layer. During outage hours, loads are served only from PV plus battery, and any grid import
CityLearn records is counted as unserved energy, charged to medical devices first. That
mismatch averaged 0.25 kWh per outage. During outages, every home is limited to a
critical-loads panel (0.35 kW of essential circuits plus its medical devices, water heater
off), identical across controllers.

Caveat: CityLearn's LSTMs were trained with working cooling. With cooling shed for long
periods they predicted indoor peaks up to 47.3 °C, and 13% of episodes peaked above 40 °C,
mostly under medical-only dispatch. We therefore report heat exposure as hours above 32.2 °C,
which is less sensitive to extreme values than degree-hours.

Figures: `figures/f6_citylearn_duration.png`, `figures/f7_citylearn_tradeoff.png`.
Tables: `results/citylearn/summary.md`.

## Limits

This is a simulation-only pilot: nine synthetic households, one city and one month, hourly
time steps and a single shared bus without network constraints. The building model is
calibrated on energy use, not on measured indoor temperatures. The controllers are rule-based
and optimisation-based. The constrained multi-agent RL policy, a physiological health twin
and real-sensor validation are planned Phase 1–2 work, and the shield is designed to wrap
that policy unchanged.

Figures: `figures/f1_duration.png`, `f2_headline_48h.png`, `f3_tradeoff.png`,
`f4_case_study.png`, `f5_battery.png`. Full tables: `results/summary.md`.
