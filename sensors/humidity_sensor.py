"""
Humidity Sensor Simulator.
Simulates indoor relative humidity readings (30-70% RH) with gradual changes.
"""

import random
from base_sensor import BaseSensor


class HumiditySensor(BaseSensor):
    """Simulates indoor humidity with gradual variation."""

    def __init__(self):
        super().__init__(
            sensor_type="humidity",
            unit="%RH",
            topic="sensors/humidity",
        )
        # Start at moderate humidity
        self.current_value = 50.0
        self.min_value = 30.0
        self.max_value = 70.0

    def generate_value(self) -> float:
        # Gradual drift
        drift = random.uniform(-0.5, 0.5)
        # events like shower, cooking or rain outside
        if random.random() < 0.03:
            drift += random.choice([-5.0, 5.0])

        # water leak or flooding
        if random.random() < 0.05:
            spike = random.uniform(90.0, 99.0)
            self.logger.warning("ANOMALY: humidity spike to %.1f%%", spike)
            return spike

        self.current_value += drift
        self.current_value = max(self.min_value, min(self.max_value, self.current_value))
        noise = random.gauss(0, 0.2)
        return self.current_value + noise


if __name__ == "__main__":
    sensor = HumiditySensor()
    sensor.run()
