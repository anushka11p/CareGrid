# Step 4: outage-duration forecaster (EAGLE-I, Arizona)

Events: >= 100 customers out, peak >= 1000, gaps <= 30 min merged. Train [2015, 2016, 2017, 2018, 2019, 2020, 2021], test [2023, 2024] (3579 / 1643 events).

## Events per year

|   year |   events |   median_h |   p90_h |   max_h |
|-------:|---------:|-----------:|--------:|--------:|
|   2015 |      157 |        1.8 |     6.2 |    31.2 |
|   2016 |      349 |        1.5 |     6   |    24.2 |
|   2017 |      486 |        2   |    13.6 |   121.5 |
|   2018 |      617 |        2.2 |    13.9 |   153   |
|   2019 |      460 |        2   |    15.8 |    67.5 |
|   2020 |      689 |        1.8 |     8.8 |    60.5 |
|   2021 |      821 |        2   |     8.8 |    65.5 |
|   2022 |      831 |        1.8 |     7.8 |   101.5 |
|   2023 |      776 |        2   |     8.5 |   262   |
|   2024 |      867 |        2   |     7.8 |    67.2 |

## Test-set quality (log duration)

| quantile   | coverage (target)   |   baseline coverage |   pinball loss |   baseline pinball |   improvement % |
|:-----------|:--------------------|--------------------:|---------------:|-------------------:|----------------:|
| P50        | 0.48 (0.5)          |                0.51 |          0.401 |              0.457 |            12.4 |
| P90        | 0.89 (0.9)          |                0.94 |          0.177 |              0.199 |            10.8 |

Coverage = share of test outages shorter than the predicted quantile.

## Forecasts for the simulated scenario

July, Maricopa County, onset 14:00 on a weekday (229 past summer-afternoon Maricopa events):

- typical: 1,261 customers out in the first hour -> median restoration **1.8 h**, P90 **5.7 h**
- large: 2,444 customers out in the first hour -> median restoration **2.2 h**, P90 **7.4 h**
