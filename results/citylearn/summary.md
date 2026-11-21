### CityLearn main results, without 24 h warning (all durations pooled, n = 112 per row)

| Controller | Medical device-hours without power | Critical energy served (%) | Person-hours indoors > 32.2 C | Person-degree-hours > 26.7 C | Essential-circuit kWh not served |
|---|---|---|---|---|---|
| Equal curtailment (status quo) | 209.2 [182.8, 236.5] | 40.0 [37.9, 42.1] | 12 [8, 18] | 459 [369, 551] | 59.2 [51.9, 67.3] |
| Rule-based critical-first | 104.8 [90.5, 119.5] | 71.2 [69.7, 72.8] | 30 [22, 39] | 774 [641, 909] | 32.6 [28.0, 37.1] |
| Priority as weight (greedy) | 81.4 [66.7, 96.4] | 81.4 [79.1, 83.8] | 32 [24, 39] | 873 [761, 992] | 43.8 [38.5, 49.4] |
| CareGrid shield (greedy) | 6.1 [4.1, 8.4] | 98.3 [97.5, 98.9] | 44 [36, 53] | 1087 [957, 1224] | 53.6 [47.7, 59.4] |
| Medical-only dispatch (bound for medical service) | 2.2 [0.8, 3.8] | 99.0 [98.2, 99.6] | 340 [291, 392] | 3793 [3246, 4352] | 136.5 [121.5, 151.1] |

### CityLearn main results, WITH 24 h warning (all durations pooled, n = 112 per row)

| Controller | Medical device-hours without power | Critical energy served (%) | Person-hours indoors > 32.2 C | Person-degree-hours > 26.7 C | Essential-circuit kWh not served |
|---|---|---|---|---|---|
| Equal curtailment (status quo) | 191.2 [166.6, 217.1] | 48.5 [45.8, 51.0] | 8 [4, 12] | 363 [282, 448] | 53.2 [45.9, 60.8] |
| Rule-based critical-first | 97.2 [83.3, 111.2] | 74.1 [72.4, 75.9] | 19 [13, 26] | 643 [524, 765] | 29.8 [25.5, 34.5] |
| Priority as weight (greedy) | 68.5 [54.3, 82.4] | 87.5 [85.0, 89.9] | 25 [19, 32] | 802 [699, 918] | 37.2 [32.1, 42.6] |
| CareGrid shield (greedy) | 4.1 [2.8, 5.8] | 99.2 [98.9, 99.5] | 40 [32, 48] | 1019 [894, 1154] | 45.3 [40.0, 50.9] |
| Medical-only dispatch (bound for medical service) | 0.1 [0.0, 0.3] | 100.0 [99.9, 100.0] | 340 [289, 393] | 3793 [3250, 4355] | 136.5 [121.5, 151.5] |

### Medical device-hours without power, by true outage duration (no warning; mean of 28 start days)

| Controller | 12 h | 24 h | 48 h | 72 h |
|---|---|---|---|---|
| Equal curtailment (status quo) | 50.1 | 123.9 | 261.0 | 401.8 |
| Rule-based critical-first | 16.8 | 57.7 | 133.5 | 211.2 |
| Priority as weight (greedy) | 3.9 | 14.9 | 105.4 | 201.5 |
| CareGrid shield (greedy) | 0.8 | 2.5 | 6.3 | 14.9 |
| Medical-only dispatch (bound for medical service) | 0.8 | 2.5 | 2.7 | 2.9 |

### Person-hours indoors above 32.2 C, by true outage duration (no warning; mean of 28 start days)

| Controller | 12 h | 24 h | 48 h | 72 h |
|---|---|---|---|---|
| Equal curtailment (status quo) | 2 | 3 | 13 | 31 |
| Rule-based critical-first | 6 | 10 | 34 | 70 |
| Priority as weight (greedy) | 10 | 15 | 36 | 66 |
| CareGrid shield (greedy) | 18 | 23 | 48 | 88 |
| Medical-only dispatch (bound for medical service) | 63 | 143 | 429 | 726 |

### Paired comparison, priority-as-weight vs CareGrid shield (Wilcoxon, no warning, all durations)

| Metric | Weight | Shield | Shield - weight | p |
|---|---|---|---|---|
| crit_device_hours_down | 81.4 | 6.1 | -75.3 | 8.5e-19 |
| person_hours_danger | 31.5 | 44.3 | +12.8 | 8.7e-19 |
| person_degree_hours | 873.3 | 1087.5 | +214.2 | 4.1e-20 |
| essential_kwh_unserved | 43.8 | 53.6 | +9.7 | 4.1e-20 |

### Sweep: Heat weight (48 h outage, no warning)

| Controller | Heat weight | Device-hours down | Person-hours > 32.2 C | Essential kWh not served |
|---|---|---|---|---|
| Priority as weight (greedy) | 0.25 | 105.4 | 36 | 53.0 |
| Priority as weight (greedy) | 0.5 | 105.4 | 36 | 53.0 |
| Priority as weight (greedy) | 1 | 105.4 | 36 | 53.0 |
| Priority as weight (greedy) | 2 | 104.8 | 32 | 57.4 |
| Priority as weight (greedy) | 4 | 104.1 | 29 | 67.5 |
| Priority as weight (greedy) | 8 | 106.2 | 25 | 75.3 |
| CareGrid shield (greedy) | 0.25 | 6.3 | 48 | 62.9 |
| CareGrid shield (greedy) | 0.5 | 6.3 | 48 | 62.9 |
| CareGrid shield (greedy) | 1 | 6.3 | 48 | 63.2 |
| CareGrid shield (greedy) | 2 | 6.4 | 42 | 68.6 |
| CareGrid shield (greedy) | 4 | 6.5 | 39 | 79.4 |
| CareGrid shield (greedy) | 8 | 6.5 | 37 | 87.9 |

### Sweep: Battery kWh per home (48 h outage, no warning)

| Controller | Battery kWh per home | Device-hours down | Person-hours > 32.2 C | Essential kWh not served |
|---|---|---|---|---|
| Equal curtailment (status quo) | 6.75 | 314.1 | 14 | 89.4 |
| Equal curtailment (status quo) | 13.5 | 261.0 | 13 | 73.8 |
| Equal curtailment (status quo) | 27 | 239.1 | 12 | 67.1 |
| Equal curtailment (status quo) | 40.5 | 225.8 | 11 | 62.9 |
| Rule-based critical-first | 6.75 | 210.8 | 30 | 65.3 |
| Rule-based critical-first | 13.5 | 133.5 | 34 | 41.5 |
| Rule-based critical-first | 27 | 82.4 | 45 | 24.8 |
| Rule-based critical-first | 40.5 | 59.6 | 50 | 18.4 |
| Priority as weight (greedy) | 6.75 | 141.2 | 40 | 70.0 |
| Priority as weight (greedy) | 13.5 | 105.4 | 36 | 53.0 |
| Priority as weight (greedy) | 27 | 89.4 | 33 | 46.8 |
| Priority as weight (greedy) | 40.5 | 82.5 | 31 | 43.4 |
| CareGrid shield (greedy) | 6.75 | 14.0 | 75 | 84.8 |
| CareGrid shield (greedy) | 13.5 | 6.3 | 48 | 63.2 |
| CareGrid shield (greedy) | 27 | 5.0 | 40 | 54.1 |
| CareGrid shield (greedy) | 40.5 | 6.4 | 39 | 49.9 |
| Medical-only dispatch (bound for medical service) | 6.75 | 8.5 | 429 | 168.0 |
| Medical-only dispatch (bound for medical service) | 13.5 | 2.7 | 429 | 168.0 |
| Medical-only dispatch (bound for medical service) | 27 | 0.9 | 429 | 168.0 |
| Medical-only dispatch (bound for medical service) | 40.5 | 0.0 | 429 | 168.0 |

### Model-validity checks

- Plan-vs-CityLearn mismatch (grid import the controller did not plan, counted against medical devices): mean 0.25 kWh per outage, max 4.0 kWh.
- Highest indoor temperature predicted by the LSTM in any run: 47.3 C (medical-only dispatch, cooling off). Runs with indoor peaks above 40 C: 13% of all episodes, concentrated in controllers that shed cooling longest.
