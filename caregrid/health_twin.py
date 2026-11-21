"""Health twin: a heat-vulnerability score for every resident of the Phoenix community.

Factors follow Kenny et al., "Heat stress in older individuals and patients with common chronic
diseases", CMAJ 182(10):1053-1060, 2010: thermoregulation declines with age, and respiratory,
cardiovascular and metabolic disease, cognitive impairment and reduced mobility raise heat risk
or make it harder to avoid. The increments below are illustrative design values chosen to rank
those factors, not a validated clinical score.

Residents are assigned consistently with the medical devices in caregrid.sim.community():
oxygen concentrator -> respiratory disease, insulin fridge -> diabetes, CPAP -> sleep apnoea,
wheelchair charger -> reduced mobility, ventilator -> respiratory failure.
"""
from dataclasses import dataclass, field

BASE = 1.0
AGE_75_84 = 0.25
AGE_85_PLUS = 0.5
CONDITION_WEIGHT = {
    "respiratory": 0.4,
    "cardiovascular": 0.4,
    "cognitive": 0.3,
    "diabetes": 0.25,
    "mobility": 0.2,
    "sleep_apnea": 0.1,
}


@dataclass
class Resident:
    age: int
    conditions: tuple = field(default_factory=tuple)

    @property
    def score(self):
        s = BASE
        if self.age >= 85:
            s += AGE_85_PLUS
        elif self.age >= 75:
            s += AGE_75_84
        return s + sum(CONDITION_WEIGHT[c] for c in self.conditions)


RESIDENTS = {
    "H1": [Resident(84, ("respiratory",))],
    "H2": [Resident(78, ("diabetes",)), Resident(80, ("sleep_apnea",))],
    "H3": [Resident(91, ("respiratory", "cognitive"))],
    "H4": [Resident(72)],
    "H5": [Resident(75, ("mobility",)), Resident(69)],
    "H6": [Resident(88, ("diabetes", "sleep_apnea"))],
    "H7": [Resident(81, ("respiratory", "cardiovascular"))],
    "H8": [Resident(70), Resident(73, ("cardiovascular",))],
    "Care facility": [
        Resident(86, ("respiratory",)), Resident(90, ("respiratory",)),
        Resident(83, ("respiratory",)), Resident(87, ("cognitive",)),
        Resident(79, ("diabetes",)), Resident(92, ("cardiovascular", "cognitive")),
    ],
}


def vulnerability(building_name):
    """A building's weight on one degree-hour of heat: the sum of its residents' scores."""
    return sum(r.score for r in RESIDENTS[building_name])


def headcount(building_name):
    """Ablation weight: every resident counts as 1."""
    return float(len(RESIDENTS[building_name]))
