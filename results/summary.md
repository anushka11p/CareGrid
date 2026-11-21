### Main results, without 24 h outage warning (all durations pooled, n = 112 per row)

| Controller | Medical device-hours without power | Critical energy served (%) | Person-hours indoors > 32.2 C | Person-degree-hours > 26.7 C |
|---|---|---|---|---|
| Equal curtailment (status quo) | 374 [332, 418] | 4.2 [3.7, 4.8] | 450 [385, 515] | 4164 [3589, 4723] |
| Rule-based critical-first | 149 [130, 170] | 67.9 [66.3, 69.6] | 511 [443, 582] | 4799 [4142, 5444] |
| Priority as weight (greedy) | 104 [85, 122] | 82.0 [79.4, 84.6] | 409 [356, 462] | 4073 [3532, 4623] |
| CareGrid shield (greedy) | 82 [65, 99] | 87.3 [84.9, 89.8] | 415 [363, 468] | 4267 [3679, 4852] |
| Priority as weight (MPC) | 1 [0, 1] | 99.9 [99.8, 99.9] | 345 [300, 389] | 3727 [3223, 4239] |
| MPC, critical weight x100 | 1 [0, 1] | 99.9 [99.8, 99.9] | 345 [301, 391] | 3727 [3210, 4248] |
| MPC planned to P90 horizon | 0 [0, 1] | 100.0 [99.9, 100.0] | 336 [295, 377] | 3723 [3243, 4206] |
| CareGrid shield + MPC | 67 [53, 82] | 89.8 [87.7, 91.8] | 415 [363, 468] | 4267 [3717, 4839] |
| CareGrid shield + P90 MPC | 67 [53, 82] | 89.8 [87.8, 91.9] | 415 [361, 471] | 4267 [3701, 4842] |
| Perfect-foresight optimum (bound) | 0 [0, 0] | 100.0 [100.0, 100.0] | 320 [278, 363] | 3613 [3115, 4115] |

### Main results, WITH 24 h outage warning (all durations pooled, n = 112 per row)

| Controller | Medical device-hours without power | Critical energy served (%) | Person-hours indoors > 32.2 C | Person-degree-hours > 26.7 C |
|---|---|---|---|---|
| Equal curtailment (status quo) | 346 [305, 388] | 16.0 [14.1, 18.1] | 380 [317, 449] | 3705 [3148, 4279] |
| Rule-based critical-first | 153 [133, 174] | 65.8 [63.8, 68.0] | 441 [376, 509] | 4227 [3593, 4859] |
| Priority as weight (greedy) | 87 [69, 105] | 86.3 [83.7, 89.0] | 343 [293, 393] | 3621 [3114, 4143] |
| CareGrid shield (greedy) | 29 [20, 38] | 96.1 [94.7, 97.3] | 373 [323, 425] | 3838 [3293, 4403] |
| Priority as weight (MPC) | 1 [0, 1] | 99.9 [99.8, 100.0] | 276 [235, 320] | 3055 [2586, 3551] |
| MPC, critical weight x100 | 1 [0, 1] | 99.9 [99.8, 100.0] | 276 [233, 320] | 3054 [2561, 3547] |
| MPC planned to P90 horizon | 0 [0, 1] | 100.0 [99.9, 100.0] | 269 [230, 312] | 3038 [2586, 3513] |
| CareGrid shield + MPC | 29 [20, 38] | 96.1 [94.8, 97.3] | 372 [320, 422] | 3826 [3288, 4384] |
| CareGrid shield + P90 MPC | 29 [20, 38] | 96.1 [94.8, 97.3] | 372 [324, 423] | 3826 [3274, 4372] |
| Perfect-foresight optimum (bound) | 0 [0, 0] | 100.0 [100.0, 100.0] | 252 [213, 293] | 2925 [2473, 3419] |

### Medical device-hours without power, by true outage duration (no warning; mean over 28 start days)

| Controller | 12 h | 24 h | 48 h | 72 h |
|---|---|---|---|---|
| Equal curtailment (status quo) | 110.0 | 226.0 | 462.0 | 698.0 |
| Rule-based critical-first | 24.0 | 75.3 | 190.0 | 305.0 |
| Priority as weight (greedy) | 0.0 | 22.2 | 138.4 | 254.6 |
| CareGrid shield (greedy) | 0.0 | 0.0 | 105.8 | 222.1 |
| Priority as weight (MPC) | 0.0 | 0.0 | 0.8 | 2.2 |
| MPC, critical weight x100 | 0.0 | 0.0 | 0.9 | 2.2 |
| MPC planned to P90 horizon | 0.0 | 0.0 | 0.0 | 1.1 |
| CareGrid shield + MPC | 0.0 | 0.0 | 76.2 | 192.5 |
| CareGrid shield + P90 MPC | 0.0 | 0.0 | 76.2 | 192.5 |
| Perfect-foresight optimum (bound) | 0.0 | 0.0 | 0.0 | 0.0 |

### Person-degree-hours above 26.7 C, by true outage duration (no warning)

| Controller | 12 h | 24 h | 48 h | 72 h |
|---|---|---|---|---|
| Equal curtailment (status quo) | 693 | 2121 | 5289 | 8553 |
| Rule-based critical-first | 887 | 2472 | 6069 | 9767 |
| Priority as weight (greedy) | 769 | 2198 | 5161 | 8165 |
| CareGrid shield (greedy) | 794 | 2275 | 5399 | 8600 |
| Priority as weight (MPC) | 745 | 1902 | 4682 | 7581 |
| MPC, critical weight x100 | 745 | 1902 | 4682 | 7581 |
| MPC planned to P90 horizon | 890 | 1963 | 4596 | 7444 |
| CareGrid shield + MPC | 794 | 2275 | 5399 | 8600 |
| CareGrid shield + P90 MPC | 794 | 2275 | 5399 | 8600 |
| Perfect-foresight optimum (bound) | 596 | 1905 | 4599 | 7353 |

### Paired comparisons (Wilcoxon signed-rank over matched scenarios, no warning, all durations)

| Comparison | Metric | Mean A | Mean B | Mean B - A | p |
|---|---|---|---|---|---|
| Priority as weight (greedy) (A) vs CareGrid shield (greedy) (B) | crit_device_hours_down | 103.8 | 82.0 | -21.8 | 1.5e-15 |
| Priority as weight (greedy) (A) vs CareGrid shield (greedy) (B) | person_degree_hours | 4073.5 | 4267.2 | +193.7 | 1.6e-19 |
| Priority as weight (MPC) (A) vs CareGrid shield + MPC (B) | crit_device_hours_down | 0.8 | 67.2 | +66.4 | 7.5e-11 |
| Priority as weight (MPC) (A) vs CareGrid shield + MPC (B) | person_degree_hours | 3727.4 | 4267.1 | +539.7 | 5.5e-20 |
| Priority as weight (MPC) (A) vs MPC planned to P90 horizon (B) | crit_device_hours_down | 0.8 | 0.3 | -0.5 | 0.0078 |
| Priority as weight (MPC) (A) vs MPC planned to P90 horizon (B) | person_degree_hours | 3727.4 | 3723.3 | -4.1 | 0.57 |
| MPC planned to P90 horizon (A) vs CareGrid shield + P90 MPC (B) | crit_device_hours_down | 0.3 | 67.2 | +66.9 | 7.5e-11 |
| MPC planned to P90 horizon (A) vs CareGrid shield + P90 MPC (B) | person_degree_hours | 3723.3 | 4267.1 | +543.8 | 1.1e-15 |
| Priority as weight (MPC) (A) vs MPC, critical weight x100 (B) | crit_device_hours_down | 0.8 | 0.8 | +0.0 | 0.33 |
| Priority as weight (MPC) (A) vs MPC, critical weight x100 (B) | person_degree_hours | 3727.4 | 3727.3 | -0.1 | 0.00021 |

### Value of a 24 h outage warning (pre-charge), mean over all scenarios

| Controller | Device-hours down: no warning | with warning | Person-degree-hours: no warning | with warning |
|---|---|---|---|---|
| Equal curtailment (status quo) | 374.0 | 346.1 | 4164 | 3705 |
| Rule-based critical-first | 148.6 | 153.2 | 4799 | 4227 |
| Priority as weight (greedy) | 103.8 | 87.1 | 4073 | 3621 |
| CareGrid shield (greedy) | 82.0 | 29.1 | 4267 | 3838 |
| Priority as weight (MPC) | 0.8 | 0.7 | 3727 | 3055 |
| MPC, critical weight x100 | 0.8 | 0.7 | 3727 | 3054 |
| MPC planned to P90 horizon | 0.3 | 0.3 | 3723 | 3038 |
| CareGrid shield + MPC | 67.2 | 29.1 | 4267 | 3826 |
| CareGrid shield + P90 MPC | 67.2 | 29.1 | 4267 | 3826 |
| Perfect-foresight optimum (bound) | 0.0 | 0.0 | 3613 | 2925 |

Battery state of charge at outage start: 30% without warning, 100% with warning. Pre-charging draws 111 kWh extra from the grid per event.

### Battery size sweep (48 h outage, no warning)

| Controller | Battery kWh | Device-hours down | Person-degree-hours |
|---|---|---|---|
| Rule-based critical-first | 75 | 214.0 | 6069 |
| Rule-based critical-first | 100 | 202.0 | 6069 |
| Rule-based critical-first | 150 | 190.0 | 6069 |
| Rule-based critical-first | 250 | 155.0 | 6069 |
| Rule-based critical-first | 400 | 114.8 | 6069 |
| Priority as weight (greedy) | 75 | 186.4 | 5186 |
| Priority as weight (greedy) | 100 | 170.5 | 5179 |
| Priority as weight (greedy) | 150 | 138.4 | 5161 |
| Priority as weight (greedy) | 250 | 116.1 | 5081 |
| Priority as weight (greedy) | 400 | 116.1 | 4889 |
| CareGrid shield (greedy) | 75 | 169.0 | 5399 |
| CareGrid shield (greedy) | 100 | 147.4 | 5399 |
| CareGrid shield (greedy) | 150 | 105.8 | 5399 |
| CareGrid shield (greedy) | 250 | 21.8 | 5399 |
| CareGrid shield (greedy) | 400 | 0.1 | 5224 |
| Priority as weight (MPC) | 75 | 0.9 | 4831 |
| Priority as weight (MPC) | 100 | 0.8 | 4773 |
| Priority as weight (MPC) | 150 | 0.8 | 4682 |
| Priority as weight (MPC) | 250 | 0.8 | 4508 |
| Priority as weight (MPC) | 400 | 0.8 | 4258 |
| MPC planned to P90 horizon | 75 | 0.0 | 4760 |
| MPC planned to P90 horizon | 100 | 0.0 | 4691 |
| MPC planned to P90 horizon | 150 | 0.0 | 4596 |
| MPC planned to P90 horizon | 250 | 0.0 | 4415 |
| MPC planned to P90 horizon | 400 | 0.0 | 4151 |
| CareGrid shield + P90 MPC | 75 | 137.5 | 5399 |
| CareGrid shield + P90 MPC | 100 | 117.2 | 5399 |
| CareGrid shield + P90 MPC | 150 | 76.2 | 5399 |
| CareGrid shield + P90 MPC | 250 | 4.1 | 5378 |
| CareGrid shield + P90 MPC | 400 | 0.1 | 5164 |
| Perfect-foresight optimum (bound) | 75 | 0.0 | 4762 |
| Perfect-foresight optimum (bound) | 100 | 0.0 | 4694 |
| Perfect-foresight optimum (bound) | 150 | 0.0 | 4599 |
| Perfect-foresight optimum (bound) | 250 | 0.0 | 4417 |
| Perfect-foresight optimum (bound) | 400 | 0.0 | 4153 |

### Heat-weight sweep (48 h outage, no warning)

| Controller | Heat weight | Device-hours down | Person-degree-hours |
|---|---|---|---|
| Priority as weight (greedy) | 0.25 | 138.4 | 5475 |
| Priority as weight (greedy) | 0.5 | 138.4 | 5400 |
| Priority as weight (greedy) | 1 | 138.4 | 5161 |
| Priority as weight (greedy) | 2 | 245.6 | 4806 |
| Priority as weight (greedy) | 4 | 316.8 | 4637 |
| Priority as weight (greedy) | 8 | 406.1 | 4497 |
| CareGrid shield (greedy) | 0.25 | 105.8 | 5399 |
| CareGrid shield (greedy) | 0.5 | 105.8 | 5399 |
| CareGrid shield (greedy) | 1 | 105.8 | 5399 |
| CareGrid shield (greedy) | 2 | 105.8 | 5399 |
| CareGrid shield (greedy) | 4 | 105.8 | 5399 |
| CareGrid shield (greedy) | 8 | 105.8 | 5399 |
| Priority as weight (MPC) | 0.25 | 0.0 | 5247 |
| Priority as weight (MPC) | 0.5 | 0.6 | 4683 |
| Priority as weight (MPC) | 1 | 0.8 | 4682 |
| Priority as weight (MPC) | 2 | 386.2 | 3922 |
| Priority as weight (MPC) | 4 | 472.0 | 3844 |
| Priority as weight (MPC) | 8 | 472.0 | 3844 |
| CareGrid shield + P90 MPC | 0.25 | 76.2 | 5399 |
| CareGrid shield + P90 MPC | 0.5 | 76.2 | 5399 |
| CareGrid shield + P90 MPC | 1 | 76.2 | 5399 |
| CareGrid shield + P90 MPC | 2 | 76.2 | 5399 |
| CareGrid shield + P90 MPC | 4 | 76.2 | 5399 |
| CareGrid shield + P90 MPC | 8 | 76.2 | 5399 |

### Shield P90 bound sensitivity (no warning; 72 h true outage, utility estimate 24 h)

| Controller | P90 bound (h) | Device-hours down | Person-degree-hours |
|---|---|---|---|
| CareGrid shield (greedy) | 24 | 229.5 | 8586 |
| CareGrid shield (greedy) | 36 | 222.1 | 8600 |
| CareGrid shield (greedy) | 48 | 222.1 | 8600 |
| CareGrid shield (greedy) | 72 | 222.2 | 8600 |
| CareGrid shield (greedy) | 96 | 222.2 | 8600 |
| CareGrid shield + P90 MPC | 24 | 223.0 | 8545 |
| CareGrid shield + P90 MPC | 36 | 192.5 | 8600 |
| CareGrid shield + P90 MPC | 48 | 192.5 | 8600 |
| CareGrid shield + P90 MPC | 72 | 192.6 | 8600 |
| CareGrid shield + P90 MPC | 96 | 192.6 | 8600 |

### Outage start-hour sensitivity (48 h outage, no warning)

| Controller | Start hour | Device-hours down | Person-degree-hours |
|---|---|---|---|
| Rule-based critical-first | 2 | 178.3 | 5314 |
| Rule-based critical-first | 8 | 190.0 | 5667 |
| Rule-based critical-first | 14 | 190.0 | 6069 |
| Rule-based critical-first | 20 | 180.1 | 5621 |
| Priority as weight (greedy) | 2 | 158.4 | 4309 |
| Priority as weight (greedy) | 8 | 170.5 | 4691 |
| Priority as weight (greedy) | 14 | 138.4 | 5161 |
| Priority as weight (greedy) | 20 | 116.1 | 4731 |
| CareGrid shield (greedy) | 2 | 109.8 | 4465 |
| CareGrid shield (greedy) | 8 | 106.9 | 4806 |
| CareGrid shield (greedy) | 14 | 105.8 | 5399 |
| CareGrid shield (greedy) | 20 | 109.1 | 4926 |
| Priority as weight (MPC) | 2 | 0.0 | 3879 |
| Priority as weight (MPC) | 8 | 0.8 | 4031 |
| Priority as weight (MPC) | 14 | 0.8 | 4682 |
| Priority as weight (MPC) | 20 | 39.1 | 4410 |
| MPC planned to P90 horizon | 2 | 0.0 | 3765 |
| MPC planned to P90 horizon | 8 | 0.0 | 3946 |
| MPC planned to P90 horizon | 14 | 0.0 | 4596 |
| MPC planned to P90 horizon | 20 | 0.0 | 4425 |
| CareGrid shield + P90 MPC | 2 | 104.3 | 4465 |
| CareGrid shield + P90 MPC | 8 | 70.3 | 4797 |
| CareGrid shield + P90 MPC | 14 | 76.2 | 5399 |
| CareGrid shield + P90 MPC | 20 | 109.1 | 4926 |
| Perfect-foresight optimum (bound) | 2 | 0.0 | 3707 |
| Perfect-foresight optimum (bound) | 8 | 0.0 | 3946 |
| Perfect-foresight optimum (bound) | 14 | 0.0 | 4599 |
| Perfect-foresight optimum (bound) | 20 | 0.0 | 4352 |

### Grid-connected July 2023 (normal operation)

- load_kwh: 28,437.1
- pv_kwh: 9,621.4
- grid_import_kwh: 18,816.2
- export_kwh: 0.0
- pv_self_consumption_pct: 100.0
- self_sufficiency_pct: 33.8
- grid_co2_t: 6.6
- co2_avoided_by_pv_t: 3.4
