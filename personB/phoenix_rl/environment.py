
import gymnasium as gym
from gymnasium import spaces
import numpy as np

from caregrid import sim


class PhoenixRLEnv(gym.Env):
    """
    Phoenix heatwave outage environment.

    The agent proposes essential and discretionary
    allocations. The existing safety shield protects
    medical devices and prioritizes thermal safety.

    Medical and thermal constraint costs are tracked
    separately for Lagrangian optimization.
    """

    metadata = {"render_modes": []}

    def __init__(self, duration=24, start=500):
        super().__init__()

        self.inp = sim.load_inputs()
        self.assets = sim.Assets()
        self.blds = sim.community()

        if start < 0 or start >= len(self.inp["hour"]):
            raise ValueError("Invalid simulation start index.")

        self.duration = min(
            duration,
            len(self.inp["hour"]) - start
        )
        self.start = start

        self.n = len(self.blds)

        self.action_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(2 * self.n,),
            dtype=np.float32
        )

        self.observation_space = spaces.Box(
            low=-100.0,
            high=100.0,
            shape=(self.n + 4,),
            dtype=np.float32
        )

        self.reset()

    def _observation(self):
        t = self.t
        temp = self.inp["temp"][t]
        ghi = self.inp["ghi"][t]
        poa = self.inp["poa"][t]

        pv = sim.pv_kw(self.assets, poa, temp)

        values = (
            self.tin
            + [self.soc, temp, ghi / 1000.0, pv / 60.0]
        )

        return np.asarray(values, dtype=np.float32)

    
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        options = options or {}

        self.start = int(options.get("start", self.start))
        requested_duration = int(
            options.get("duration", self.duration)
        )

        if self.start < 0 or self.start >= len(self.inp["hour"]):
            raise ValueError("Invalid simulation start index.")

        if requested_duration <= 0:
            raise ValueError("Duration must be positive.")

        self.duration = min(
            requested_duration,
            len(self.inp["hour"]) - self.start
        )

        self.t = self.start
        self.steps = 0
        self.soc = 0.90

        self.tin = [sim.SETPOINT_C] * self.n

        self.total_reward = 0.0
        self.medical_down = 0
        self.danger_hours = 0
        self.danger_degree_hours = 0.0

        self.total_medical_cost = 0.0
        self.total_thermal_cost = 0.0

        return self._observation(), {}


    def step(self, action):
        action = np.asarray(action, dtype=np.float32)
        action = np.clip(action, 0.0, 1.0)

        t = self.t
        temp = self.inp["temp"][t]
        ghi = self.inp["ghi"][t]

        pv = sim.pv_kw(
            self.assets,
            self.inp["poa"][t],
            temp
        )

        cap = self.assets.batt_kwh

        batt_kwh = max(
            0.0,
            (self.soc - self.assets.soc_min)
            * cap * self.assets.eta
        )

        batt_kw = min(self.assets.batt_kw, batt_kwh)

        ctx = {
            "t": t,
            "pv": pv,
            "soc": self.soc,
            "batt_kwh_avail": batt_kwh,
            "batt_kw_avail": batt_kw,
            "supply": pv + batt_kw,
            "forecast_end": self.start + self.duration,
            "w_heat": 1.0,
            "reserve_kwh": 0.0,
            "eta": self.assets.eta,
            "batt_kw": self.assets.batt_kw,
        }

        rows = sim._demands(
            self.inp, self.blds, t, self.tin
        )

        proposal = []

        for i, row in enumerate(rows):
            proposal.append({
                "ess": float(action[2 * i]) * row["ess"],
                "disc": float(action[2 * i + 1]) * row["disc"]
            })

        decisions = sim.apply_shield(rows, ctx, proposal)

        used = 0.0
        reward = 0.0

        medical_cost = 0.0
        thermal_cost = 0.0

        danger_people = 0
        device_down = 0

        for i, (building, row, decision) in enumerate(
            zip(self.blds, rows, decisions)
        ):

            served = sum(
                kw for kw, ok in zip(
                    row["devices"], decision["devices"]
                ) if ok
            )

            unmet_critical = max(
                0.0,
                sum(row["devices"]) - served
            )

            used += (
                served
                + decision["ess"]
                + decision["disc"]
                + decision["ac"]
            )

            old_temp = self.tin[i]

            self.tin[i] = sim.next_temp(
                building,
                old_temp,
                temp,
                ghi,
                decision["ac"]
            )

            device_down += sum(
                1 for ok in decision["devices"] if not ok
            )

            temperature_excess = max(
                0.0,
                self.tin[i] - sim.DANGER_C
            )

            if temperature_excess > 0:
                danger_people += building.residents

            reward += (
                10.0 * served
                + 2.0 * decision["ess"]
                + 0.5 * decision["ac"]
                + 0.1 * decision["disc"]
            )

            medical_cost += unmet_critical

            thermal_cost += (
                building.residents * temperature_excess
            )

        # Battery update.
        net = used - pv

        if net > 0:
            self.soc -= net / self.assets.eta / cap
        else:
            charge = min(
                -net,
                self.assets.batt_kw,
                (1.0 - self.soc) * cap / self.assets.eta
            )
            self.soc += charge * self.assets.eta / cap

        self.soc = float(np.clip(
            self.soc,
            self.assets.soc_min,
            1.0
        ))

        self.medical_down += device_down
        self.danger_hours += danger_people
        self.danger_degree_hours += thermal_cost

        self.total_medical_cost += medical_cost
        self.total_thermal_cost += thermal_cost

        self.steps += 1
        self.t += 1

        terminated = self.steps >= self.duration
        truncated = False

        if not terminated:
            observation = self._observation()
        else:
            observation = np.asarray(
                self.tin + [self.soc, 0.0, 0.0, 0.0],
                dtype=np.float32
            )

        self.total_reward += reward

        info = {
            "constraint_cost": float(
                10.0 * medical_cost + thermal_cost
            ),
            "medical_constraint_cost": float(medical_cost),
            "thermal_constraint_cost": float(thermal_cost),
            "medical_devices_down": int(device_down),
            "danger_people": int(danger_people),
            "danger_degree_hours": float(thermal_cost),
            "battery_soc": self.soc,
        }

        return (
            observation,
            float(reward),
            terminated,
            truncated,
            info
        )

