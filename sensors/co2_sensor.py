"""
CO₂ Sensor Simulator.
Simulates indoor CO₂ levels (400-2000 ppm) with realistic patterns.
"""

import random
from base_sensor import BaseSensor


class CO2Sensor(BaseSensor):
    """Simulates indoor CO₂ levels with occupancy-based spikes."""

    def __init__(self):
        super().__init__(
            sensor_type="co2",
            unit="ppm",
            topic="sensors/co2",
        )
        # Start at outdoor baseline CO₂
        self.current_value = 450.0
        self.min_value = 400.0
        self.max_value = 2000.0

    def generate_value(self) -> float:
        # simulating people breathing in a room
        drift = random.uniform(-1.0, 3.0)
        # simulating more people or cooking
        if random.random() < 0.05:
            drift += random.uniform(50, 150)
        # window opened, somme ventilation
        if random.random() < 0.03:
            drift -= random.uniform(50, 100)

        # gas leak or ventilation failure
        if random.random() < 0.05:
            spike = random.uniform(2500.0, 5000.0)
            self.logger.warning("ANOMALY: CO2 spike to %.0f ppm", spike)
            return spike

        self.current_value += drift
        self.current_value = max(self.min_value, min(self.max_value, self.current_value))
        noise = random.gauss(0, 5)
        return self.current_value + noise


if __name__ == "__main__":
    sensor = CO2Sensor()
    sensor.run()
