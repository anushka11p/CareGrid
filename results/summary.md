### Main results, without 24 h outage warning (all durations pooled, n = 112 per row)

| Controller | Medical device-hours without power | Critical energy served (%) | Person-hours indoors > 32.2 C | Person-degree-hours > 26.7 C |
|---|---|---|---|---|
| Equal curtailment (status quo) | 374 [332, 418] | 4.2 [3.7, 4.8] | 450 [385, 515] | 4164 [3589, 4723] |
| Rule-based critical-first | 149 [130, 170] | 67.9 [66.3, 69.6] | 511 [443, 582] | 4799 [4142, 5444] |
| Priority as weight (greedy) | 104 [85, 122] | 82.0 [79.4, 84.6] | 409 [356, 462] | 4073 [3532, 4623] |
| CareGrid shield (greedy) | 0 [0, 0] | 100.0 [100.0, 100.0] | 425 [371, 481] | 4211 [3643, 4780] |
| Priority as weight (MPC) | 1 [0, 1] | 99.9 [99.8, 99.9] | 345 [300, 389] | 3727 [3223, 4239] |
| MPC, critical weight x100 | 1 [0, 1] | 99.9 [99.8, 99.9] | 345 [301, 391] | 3727 [3210, 4248] |
| MPC planned to P90 horizon | 0 [0, 1] | 100.0 [99.9, 100.0] | 336 [295, 377] | 3723 [3243, 4206] |
| CareGrid shield + MPC | 0 [0, 0] | 100.0 [100.0, 100.0] | 425 [370, 481] | 4211 [3674, 4767] |
| CareGrid shield + P90 MPC | 0 [0, 0] | 100.0 [100.0, 100.0] | 425 [369, 484] | 4211 [3659, 4767] |
| Perfect-foresight optimum (bound) | 0 [0, 0] | 100.0 [100.0, 100.0] | 320 [278, 363] | 3613 [3115, 4115] |

### Main results, WITH 24 h outage warning (all durations pooled, n = 112 per row)

| Controller | Medical device-hours without power | Critical energy served (%) | Person-hours indoors > 32.2 C | Person-degree-hours > 26.7 C |
|---|---|---|---|---|
| Equal curtailment (status quo) | 346 [305, 388] | 16.0 [14.1, 18.1] | 380 [317, 449] | 3705 [3148, 4279] |
| Rule-based critical-first | 153 [133, 174] | 65.8 [63.8, 68.0] | 441 [376, 509] | 4227 [3593, 4859] |
| Priority as weight (greedy) | 87 [69, 105] | 86.3 [83.7, 89.0] | 343 [293, 393] | 3621 [3114, 4143] |
| CareGrid shield (greedy) | 0 [0, 0] | 100.0 [100.0, 100.0] | 351 [300, 402] | 3656 [3134, 4199] |
| Priority as weight (MPC) | 1 [0, 1] | 99.9 [99.8, 100.0] | 276 [235, 320] | 3055 [2586, 3551] |
| MPC, critical weight x100 | 1 [0, 1] | 99.9 [99.8, 100.0] | 276 [233, 320] | 3054 [2561, 3547] |
| MPC planned to P90 horizon | 0 [0, 1] | 100.0 [99.9, 100.0] | 269 [230, 311] | 3038 [2586, 3513] |
| CareGrid shield + MPC | 0 [0, 0] | 100.0 [100.0, 100.0] | 350 [298, 401] | 3646 [3128, 4186] |
| CareGrid shield + P90 MPC | 0 [0, 0] | 100.0 [100.0, 100.0] | 350 [301, 401] | 3646 [3113, 4172] |
| Perfect-foresight optimum (bound) | 0 [0, 0] | 100.0 [100.0, 100.0] | 252 [213, 293] | 2925 [2473, 3419] |

### Medical device-hours without power, by true outage duration (no warning; mean over 28 start days)

| Controller | 12 h | 24 h | 48 h | 72 h |
|---|---|---|---|---|
| Equal curtailment (status quo) | 110.0 | 226.0 | 462.0 | 698.0 |
| Rule-based critical-first | 24.0 | 75.3 | 190.0 | 305.0 |
| Priority as weight (greedy) | 0.0 | 22.2 | 138.4 | 254.6 |
| CareGrid shield (greedy) | 0.0 | 0.0 | 0.1 | 0.1 |
| Priority as weight (MPC) | 0.0 | 0.0 | 0.8 | 2.2 |
| MPC, critical weight x100 | 0.0 | 0.0 | 0.9 | 2.2 |
| MPC planned to P90 horizon | 0.0 | 0.0 | 0.0 | 1.1 |
| CareGrid shield + MPC | 0.0 | 0.0 | 0.1 | 0.1 |
| CareGrid shield + P90 MPC | 0.0 | 0.0 | 0.1 | 0.1 |
| Perfect-foresight optimum (bound) | 0.0 | 0.0 | 0.0 | 0.0 |

### Person-degree-hours above 26.7 C, by true outage duration (no warning)

| Controller | 12 h | 24 h | 48 h | 72 h |
|---|---|---|---|---|
| Equal curtailment (status quo) | 693 | 2121 | 5289 | 8553 |
| Rule-based critical-first | 887 | 2472 | 6069 | 9767 |
| Priority as weight (greedy) | 769 | 2198 | 5161 | 8165 |
| CareGrid shield (greedy) | 847 | 2307 | 5251 | 8439 |
| Priority as weight (MPC) | 745 | 1902 | 4682 | 7581 |
| MPC, critical weight x100 | 745 | 1902 | 4682 | 7581 |
| MPC planned to P90 horizon | 890 | 1963 | 4596 | 7444 |
| CareGrid shield + MPC | 847 | 2307 | 5251 | 8439 |
| CareGrid shield + P90 MPC | 847 | 2307 | 5251 | 8439 |
| Perfect-foresight optimum (bound) | 596 | 1905 | 4599 | 7353 |

### Paired comparisons (Wilcoxon signed-rank over matched scenarios, no warning, all durations)

| Comparison | Metric | Mean A | Mean B | Mean B - A | p |
|---|---|---|---|---|---|
| Priority as weight (greedy) (A) vs CareGrid shield (greedy) (B) | crit_device_hours_down | 103.8 | 0.1 | -103.7 | 1.6e-15 |
| Priority as weight (greedy) (A) vs CareGrid shield (greedy) (B) | person_degree_hours | 4073.5 | 4210.9 | +137.4 | 3.5e-15 |
| Priority as weight (MPC) (A) vs CareGrid shield + MPC (B) | crit_device_hours_down | 0.8 | 0.1 | -0.7 | 0.0063 |
| Priority as weight (MPC) (A) vs CareGrid shield + MPC (B) | person_degree_hours | 3727.4 | 4210.9 | +483.5 | 4.1e-20 |
| Priority as weight (MPC) (A) vs MPC planned to P90 horizon (B) | crit_device_hours_down | 0.8 | 0.3 | -0.5 | 0.0078 |
| Priority as weight (MPC) (A) vs MPC planned to P90 horizon (B) | person_degree_hours | 3727.4 | 3723.3 | -4.1 | 0.57 |
| MPC planned to P90 horizon (A) vs CareGrid shield + P90 MPC (B) | crit_device_hours_down | 0.3 | 0.1 | -0.2 | 0.2 |
| MPC planned to P90 horizon (A) vs CareGrid shield + P90 MPC (B) | person_degree_hours | 3723.3 | 4210.9 | +487.6 | 6.8e-16 |
| Priority as weight (MPC) (A) vs MPC, critical weight x100 (B) | crit_device_hours_down | 0.8 | 0.8 | +0.0 | 0.33 |
| Priority as weight (MPC) (A) vs MPC, critical weight x100 (B) | person_degree_hours | 3727.4 | 3727.3 | -0.1 | 8.6e-05 |

### Value of a 24 h outage warning (pre-charge), mean over all scenarios

| Controller | Device-hours down: no warning | with warning | Person-degree-hours: no warning | with warning |
|---|---|---|---|---|
| Equal curtailment (status quo) | 374.0 | 346.1 | 4164 | 3705 |
| Rule-based critical-first | 148.6 | 153.2 | 4799 | 4227 |
| Priority as weight (greedy) | 103.8 | 87.1 | 4073 | 3621 |
| CareGrid shield (greedy) | 0.1 | 0.1 | 4211 | 3656 |
| Priority as weight (MPC) | 0.8 | 0.7 | 3727 | 3055 |
| MPC, critical weight x100 | 0.8 | 0.7 | 3727 | 3054 |
| MPC planned to P90 horizon | 0.3 | 0.3 | 3723 | 3038 |
| CareGrid shield + MPC | 0.1 | 0.1 | 4211 | 3646 |
| CareGrid shield + P90 MPC | 0.1 | 0.1 | 4211 | 3646 |
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
| CareGrid shield (greedy) | 75 | 0.1 | 5370 |
| CareGrid shield (greedy) | 100 | 0.1 | 5334 |
| CareGrid shield (greedy) | 150 | 0.1 | 5251 |
| CareGrid shield (greedy) | 250 | 0.1 | 5116 |
| CareGrid shield (greedy) | 400 | 0.1 | 4927 |
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
| CareGrid shield + P90 MPC | 75 | 0.1 | 5370 |
| CareGrid shield + P90 MPC | 100 | 0.1 | 5334 |
| CareGrid shield + P90 MPC | 150 | 0.1 | 5251 |
| CareGrid shield + P90 MPC | 250 | 0.1 | 5097 |
| CareGrid shield + P90 MPC | 400 | 0.1 | 4862 |
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
| CareGrid shield (greedy) | 0.25 | 0.1 | 5251 |
| CareGrid shield (greedy) | 0.5 | 0.1 | 5251 |
| CareGrid shield (greedy) | 1 | 0.1 | 5251 |
| CareGrid shield (greedy) | 2 | 0.1 | 5251 |
| CareGrid shield (greedy) | 4 | 0.1 | 5251 |
| CareGrid shield (greedy) | 8 | 0.1 | 5251 |
| Priority as weight (MPC) | 0.25 | 0.0 | 5247 |
| Priority as weight (MPC) | 0.5 | 0.6 | 4683 |
| Priority as weight (MPC) | 1 | 0.8 | 4682 |
| Priority as weight (MPC) | 2 | 386.2 | 3922 |
| Priority as weight (MPC) | 4 | 472.0 | 3844 |
| Priority as weight (MPC) | 8 | 472.0 | 3844 |
| CareGrid shield + P90 MPC | 0.25 | 0.1 | 5251 |
| CareGrid shield + P90 MPC | 0.5 | 0.1 | 5251 |
| CareGrid shield + P90 MPC | 1 | 0.1 | 5251 |
| CareGrid shield + P90 MPC | 2 | 0.1 | 5251 |
| CareGrid shield + P90 MPC | 4 | 0.1 | 5251 |
| CareGrid shield + P90 MPC | 8 | 0.1 | 5251 |

### Shield P90 bound sensitivity (no warning; 72 h true outage, utility estimate 24 h)

| Controller | P90 bound (h) | Device-hours down | Person-degree-hours |
|---|---|---|---|
| CareGrid shield (greedy) | 24 | 0.1 | 8517 |
| CareGrid shield (greedy) | 36 | 0.1 | 8438 |
| CareGrid shield (greedy) | 48 | 0.1 | 8439 |
| CareGrid shield (greedy) | 72 | 0.1 | 8458 |
| CareGrid shield (greedy) | 96 | 0.0 | 8683 |
| CareGrid shield + P90 MPC | 24 | 0.1 | 8454 |
| CareGrid shield + P90 MPC | 36 | 0.1 | 8438 |
| CareGrid shield + P90 MPC | 48 | 0.1 | 8439 |
| CareGrid shield + P90 MPC | 72 | 0.1 | 8458 |
| CareGrid shield + P90 MPC | 96 | 0.0 | 8683 |

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
| CareGrid shield (greedy) | 2 | 0.0 | 4436 |
| CareGrid shield (greedy) | 8 | 0.1 | 4658 |
| CareGrid shield (greedy) | 14 | 0.1 | 5251 |
| CareGrid shield (greedy) | 20 | 0.0 | 4965 |
| Priority as weight (MPC) | 2 | 0.0 | 3879 |
| Priority as weight (MPC) | 8 | 0.8 | 4031 |
| Priority as weight (MPC) | 14 | 0.8 | 4682 |
| Priority as weight (MPC) | 20 | 39.1 | 4410 |
| MPC planned to P90 horizon | 2 | 0.0 | 3765 |
| MPC planned to P90 horizon | 8 | 0.0 | 3946 |
| MPC planned to P90 horizon | 14 | 0.0 | 4596 |
| MPC planned to P90 horizon | 20 | 0.0 | 4425 |
| CareGrid shield + P90 MPC | 2 | 0.0 | 4436 |
| CareGrid shield + P90 MPC | 8 | 0.1 | 4646 |
| CareGrid shield + P90 MPC | 14 | 0.1 | 5251 |
| CareGrid shield + P90 MPC | 20 | 0.0 | 4965 |
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
