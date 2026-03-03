"""
Temperature Sensor Simulator.
Simulates indoor temperature readings (18-30°C) with gradual change.
"""

import random
from base_sensor import BaseSensor


class TemperatureSensor(BaseSensor):
    """Simulates indoor temperature with a realistic patterns."""

    def __init__(self):
        super().__init__(
            sensor_type="temperature",
            unit="°C",
            topic="sensors/temperature",
        )
        # Start at a comfortable room temperature
        self.current_value = 22.0
        self.min_value = 18.0
        self.max_value = 30.0

    def generate_value(self) -> float:
        drift = random.uniform(-0.3, 0.3)
        # Occasional larger changes
        if random.random() < 0.05:
            drift += random.choice([-2.0, 2.0])

        # fire or heater malfunction 
        if random.random() < 0.05:
            spike = random.uniform(45.0, 55.0)
            self.logger.warning("ANOMALY: temperature spike to %.1f°C", spike)
            return spike

        self.current_value += drift
        self.current_value = max(self.min_value, min(self.max_value, self.current_value))
        noise = random.gauss(0, 0.1)
        return self.current_value + noise


if __name__ == "__main__":
    sensor = TemperatureSensor()
    sensor.run()
