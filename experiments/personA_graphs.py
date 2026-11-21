
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Load the combined experiment results
df = pd.read_csv("results/personA_outage_summary.csv")

# Create folder to save graphs
output = Path("results/personA_graphs")
output.mkdir(parents=True, exist_ok=True)

# Metrics to plot
metrics = [
    ("crit_device_hours_down",
     "Critical Medical Device Downtime",
     "Device Hours Down",
     "01_critical_device_downtime.png"),

    ("crit_kwh_unserved",
     "Critical Medical Energy Unserved",
     "Energy Unserved (kWh)",
     "02_critical_energy_unserved.png"),

    ("hw_ens",
     "Household Energy Not Served",
     "Energy Not Served (kWh)",
     "03_household_energy_shortage.png"),

    ("max_tin",
     "Maximum Indoor Temperature",
     "Maximum Temperature (°C)",
     "04_maximum_indoor_temperature.png")
]

# Generate one graph for each metric
for column, title, ylabel, filename in metrics:

    plt.figure(figsize=(9, 5))

    for controller in ["soft", "shield", "mpc_shield"]:

        data = df[df["controller"] == controller]
        data = data.sort_values("duration_h")

        plt.plot(
            data["duration_h"],
            data[column],
            marker="o",
            linewidth=2,
            label=controller.replace("_", " ").title()
        )

    plt.title(title)
    plt.xlabel("Outage Duration (Hours)")
    plt.ylabel(ylabel)
    plt.xticks([12, 24, 48, 72])
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    plt.savefig(output / filename, dpi=300)
    plt.close()

    print("Saved:", filename)

print("\nAll 4 graphs generated successfully!")
print("Location:", output)
