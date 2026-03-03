"""
PM2.5 Air Quality Sensor Simulator.
Simulates indoor particulate matter (0-100 µg/m³) readings.
"""

import random
from base_sensor import BaseSensor


class PM25Sensor(BaseSensor):
    """Simulates indoor PM2.5 air quality readings."""

    def __init__(self):
        super().__init__(
            sensor_type="pm25",
            unit="µg/m³",
            topic="sensors/pm25",
        )
        # Start at good air quality
        self.current_value = 12.0
        self.min_value = 0.0
        self.max_value = 100.0

    def generate_value(self) -> float:
        # Slow drift
        drift = random.uniform(-0.5, 0.5)
        # pollution event (cooking, candles, outside pollution)
        if random.random() < 0.04:
            drift += random.uniform(10, 30)
        # Gradual returning back to natural air
        if self.current_value > 15:
            drift -= (self.current_value - 15) * 0.1  # natural settling

        # nearby fire or heavy pollution
        if random.random() < 0.05:
            spike = random.uniform(150.0, 300.0)
            self.logger.warning("ANOMALY: PM2.5 spike to %.1f µg/m³", spike)
            return spike

        self.current_value += drift
        self.current_value = max(self.min_value, min(self.max_value, self.current_value))
        noise = random.gauss(0, 0.5)
        return max(0, self.current_value + noise)


if __name__ == "__main__":
    sensor = PM25Sensor()
    sensor.run()
