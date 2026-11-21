# Step 4: outage-duration forecaster (EAGLE-I, Arizona)

Events: >= 100 customers out, peak >= 1000, gaps <= 30 min merged. Train [np.int32(2015), np.int32(2016)], test [np.int32(2017)] (506 / 486 events).

## Events per year

|   year |   events |   median_h |   p90_h |   max_h |
|-------:|---------:|-----------:|--------:|--------:|
|   2015 |      157 |        1.8 |     6.2 |    31.2 |
|   2016 |      349 |        1.5 |     6   |    24.2 |
|   2017 |      486 |        2   |    13.6 |   121.5 |

## Test-set quality (log duration)

| quantile   | coverage (target)   |   baseline coverage |   pinball loss |   baseline pinball |   improvement % |
|:-----------|:--------------------|--------------------:|---------------:|-------------------:|----------------:|
| P50        | 0.43 (0.5)          |                0.38 |           0.43 |              0.516 |            16.7 |
| P90        | 0.76 (0.9)          |                0.79 |           0.25 |              0.255 |             2   |

Coverage = share of test outages shorter than the predicted quantile.

## Forecasts for the simulated scenario

July, Maricopa County, onset 14:00 on a weekday (46 past summer-afternoon Maricopa events):

- typical: 1,270 customers out in the first hour -> median restoration **1.8 h**, P90 **4.1 h**
- large: 2,390 customers out in the first hour -> median restoration **1.6 h**, P90 **4.5 h**
