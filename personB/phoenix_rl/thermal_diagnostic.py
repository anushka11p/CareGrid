import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from caregrid import sim
from personB.phoenix_rl.environment import PhoenixRLEnv

env = PhoenixRLEnv(start=300)
obs, info = env.reset(seed=42)

print("\nPHOENIX THERMAL DIAGNOSTIC")
print("=" * 55)

for hour in range(24):
    action = env.action_space.sample() * 0
    obs, reward, terminated, truncated, info = env.step(action)

    print(
        f"Hour {hour + 1:02d} | "
        f"Thermal cost: {info.get('thermal_constraint_cost', 0):.2f} | "
        f"Medical cost: {info.get('medical_constraint_cost', 0):.2f} | "
        f"Danger people: {info.get('danger_people', 0)} | "
        f"Danger degree-hours: {info.get('danger_degree_hours', 0):.2f} | "
        f"Battery SOC: {info.get('battery_soc', 0):.3f}"
    )

    if terminated or truncated:
        break

env.close()
print("\nDiagnostic completed.")