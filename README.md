# CareGrid pilot simulation

Preliminary, reproducible evidence for the CareGrid proposal. It tests the core claim from
the research briefing: protecting elderly residents' medical loads works better as a **hard
constraint enforced by a runtime shield** than as a **weight in the reward**.

Eight elderly households and a six-bed care facility share a 60 kWp PV array and a 150 kWh
community battery in Phoenix, AZ. The grid fails during the real July 2023 heatwave, the
microgrid islands, and a controller decides each hour which loads get the energy.

## Real inputs

| Input | Source |
|---|---|
| Hourly air temperature, humidity, horizontal and tilted irradiance, Phoenix, 30 Jun to 3 Aug 2023 | Open-Meteo historical archive (ERA5 reanalysis) |
| Household base-load shape (non-cooling, by hour) and cooling-energy calibration target | NREL ResStock 2021 AMY2018, Maricopa County single-family detached, July |
| Medical device wattages, heat thresholds | Research briefing (Document 11) quantitative anchors; NWS heat-index bands |

`data/fetch_data.py` downloads everything; no API keys.

## Controllers

| Name | Idea |
|---|---|
| `equal` | Status quo. All loads curtailed by the same fraction; medical devices trip below full power |
| `rule` | Critical, then essential loads; AC only when battery > 40% |
| `soft` | Priority as a **reward weight**; greedy by value per kWh; battery paced to the utility's 24 h estimate |
| `shield` | **CareGrid**: same as `soft`, plus a runtime shield that serves critical devices first and locks a battery reserve covering them to the worst-case (P90 = 48 h) restoration time |
| `mpc` / `mpc_hi` | Receding-horizon LP with a perfect weather forecast, planning to the 24 h estimate; medical weight 10 or 1000 |
| `mpc_p90` | Same LP planned to the P90 horizon |
| `mpc_shield`, `mpc_p90_shield` | The MPC policies wrapped in the same shield (the shield is policy-agnostic) |
| `oracle` | Perfect foresight of the true duration, LP relaxation. Upper bound only |

## Reproduce

```bash
python3 data/fetch_data.py        # real weather + NREL loads
python3 experiments/calibrate.py  # check the house model against ResStock
python3 experiments/run_pilot.py  # 6,048 simulated outages (~7 min) -> results/scenarios.csv
python3 experiments/analyze.py    # tables -> results/summary.md, figures -> figures/
python3 tests/test_parity.py      # browser engine == Python engine (needs Node)
python3 demo/build.py             # self-contained interactive demo -> demo/caregrid_demo.html
```

Needs Python 3.10+ with numpy, pandas, scipy, matplotlib.

## CityLearn replication (`citylearn_port/`)

The same controllers re-run on the CityLearn v3.0.2 platform, using its built-in
`tx_travis_county_neighborhood` dataset: real NREL ResStock homes in Austin, TX, measured
2018 weather (Camp Mabry), and CityLearn's per-home LSTM indoor-temperature models. Ten homes,
each with 6 kW of PV (output from NREL PVWatts v8 via PySAM) and a 13.5 kWh / 5 kW battery.

```bash
uv venv --python 3.11 .venv-citylearn
uv pip install --python .venv-citylearn/bin/python citylearn nrel-pysam
.venv-citylearn/bin/python citylearn_port/prepare.py          # build the CareGrid dataset
.venv-citylearn/bin/python citylearn_port/run_citylearn.py    # 2,016 episodes (~11 min)
.venv-citylearn/bin/python citylearn_port/analyze_citylearn.py
```

Two choices to report in the methods:

- **Islanding is enforced in the controller layer.** In CityLearn 3.0.2's built-in outage
  mode, batteries cannot discharge: the local-load estimate that caps discharge is taken
  before loads are energised and is net of PV, so it comes out as zero. CityLearn therefore
  runs grid-connected. During outage hours, controllers serve load only from PV plus battery,
  and any grid import CityLearn still records is counted as unserved energy (charged to
  medical devices first).
- **Critical-loads panel.** During outages each home serves 0.35 kW of essential circuits
  plus its medical devices, and the water heater is off. This is identical for every
  controller.

## Limits (state these in the proposal)

- Simulation only. Nine synthetic households, one city, one month, hourly time step.
- 1R1C building model calibrated on energy only, not on measured indoor temperatures.
- Single shared bus. No distribution-network constraints (voltage, line limits).
- Base load is a ResStock 2018 average shape, not metered data from elderly homes.
- Constant grid carbon factor (eGRID AZNM assumption) for the grid-connected month.
- Controllers are rule- and optimisation-based. The constrained multi-agent RL policy is
  Phase 1 work; the shield is built to wrap it.
