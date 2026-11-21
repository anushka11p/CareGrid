# Step 3: health twin

## Scores

| home          |   residents | ages                   | conditions                                                                            |   vulnerability |
|:--------------|------------:|:-----------------------|:--------------------------------------------------------------------------------------|----------------:|
| H1            |           1 | 84                     | respiratory                                                                           |            1.65 |
| H2            |           2 | 78, 80                 | diabetes; sleep_apnea                                                                 |            2.85 |
| H3            |           1 | 91                     | respiratory, cognitive                                                                |            2.2  |
| H4            |           1 | 72                     | none                                                                                  |            1    |
| H5            |           2 | 75, 69                 | mobility; none                                                                        |            2.45 |
| H6            |           1 | 88                     | diabetes, sleep_apnea                                                                 |            1.85 |
| H7            |           1 | 81                     | respiratory, cardiovascular                                                           |            2.05 |
| H8            |           2 | 70, 73                 | none; cardiovascular                                                                  |            2.4  |
| Care facility |           6 | 86, 90, 83, 87, 79, 92 | respiratory; respiratory; respiratory; cognitive; diabetes; cardiovascular, cognitive |           10.95 |

## Ablation (shield, 112 outages, paired)

| metric                 |   building order |   health twin |   change % | outages better / worse   |       p |
|:-----------------------|-----------------:|--------------:|-----------:|:-------------------------|--------:|
| vuln_degree_hours      |           7413.2 |        6590.7 |      -11.1 | 112 / 0                  | 4.1e-20 |
| person_degree_hours    |           4486.3 |        4210.9 |       -6.1 | 112 / 0                  | 4.1e-20 |
| person_hours_danger    |            428.9 |         425   |       -0.9 | 74 / 37                  | 0.038   |
| crit_device_hours_down |              0.1 |           0.1 |        0   | 0 / 0                    | 1       |
