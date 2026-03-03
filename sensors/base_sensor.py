"""
Base Sensor class for the Smart Home Air Quality Monitor.
All sensor simulators inherit from this class.
"""

import json
import time
import random
import os
import logging
from datetime import datetime, timezone
from abc import ABC, abstractmethod

import paho.mqtt.client as mqtt

# logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)


class BaseSensor(ABC):
    """
    Base class for all sensor that I will simulate.

    Config via environment variables:
        MQTT_BROKER_HOST: MQTT broker hostname (default: mosquitto)
        MQTT_BROKER_PORT: MQTT broker port (default: 1883)
        SENSOR_FREQUENCY: Seconds between readings (default: 5)
        HOUSE_ID: Identifier for the house (default: house_001)
    """

    def __init__(self, sensor_type: str, unit: str, topic: str):
        self.sensor_type = sensor_type
        self.unit = unit
        self.topic = topic
        self.house_id = os.getenv("HOUSE_ID", "house_001")
        self.frequency = float(os.getenv("SENSOR_FREQUENCY", "5"))

        self.logger = logging.getLogger(sensor_type)

        # MQTT setup
        broker_host = os.getenv("MQTT_BROKER_HOST", "mosquitto")
        broker_port = int(os.getenv("MQTT_BROKER_PORT", "1883"))

        self.client = mqtt.Client(
            client_id=f"{self.house_id}_{self.sensor_type}",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

        self.logger.info(
            "Connecting to MQTT broker at %s:%d", broker_host, broker_port
        )
        self._connect_with_retry(broker_host, broker_port)

    def _connect_with_retry(self, host: str, port: int, max_retries: int = 10):
        """Retry MQTT connection with exponential backoff."""
        for attempt in range(1, max_retries + 1):
            try:
                self.client.connect(host, port, keepalive=60)
                self.client.loop_start()
                return
            except ConnectionRefusedError:
                wait = min(2 ** attempt, 30)
                self.logger.warning(
                    "Connection attempt %d/%d failed. Retrying in %ds...",
                    attempt, max_retries, wait,
                )
                time.sleep(wait)
        raise ConnectionError(
            f"Could not connect to MQTT broker after {max_retries} attempts"
        )

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        self.logger.info("Connected to MQTT broker (rc=%s)", rc)

    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        self.logger.warning("Disconnected from MQTT broker (rc=%s)", rc)

    @abstractmethod
    def generate_value(self) -> float:
        """Generate a simulated sensor reading. Must be implemented by subclass."""
        pass

    def build_payload(self, value: float) -> dict:
        """Build the JSON for a sensor reading."""
        return {
            "sensor_type": self.sensor_type,
            "value": round(value, 2),
            "unit": self.unit,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "house_id": self.house_id,
        }

    def publish(self, payload: dict):
        """Publish a reading to the MQTT topic."""
        message = json.dumps(payload)
        result = self.client.publish(self.topic, message, qos=1)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            self.logger.info(
                "Published: %s = %s %s",
                self.sensor_type, payload["value"], self.unit,
            )
        else:
            self.logger.error("Failed to publish message (rc=%s)", result.rc)

    def run(self):
        """Main loop: generate readings and publish at configured frequency."""
        self.logger.info(
            "Starting %s sensor (frequency=%.1fs, house=%s)",
            self.sensor_type, self.frequency, self.house_id,
        )
        try:
            while True:
                value = self.generate_value()
                payload = self.build_payload(value)
                self.publish(payload)
                time.sleep(self.frequency)
        except KeyboardInterrupt:
            self.logger.info("Sensor stopped by user")
        finally:
            self.client.loop_stop()
            self.client.disconnect()
