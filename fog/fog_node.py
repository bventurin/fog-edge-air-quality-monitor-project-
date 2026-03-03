"""
Fog Node — Subscribes to sensor MQTT topics, processes data, and dispatches to cloud.

"""

import json
import os
import time
import logging
import threading
import statistics
from decimal import Decimal
from datetime import datetime, timezone
from collections import defaultdict
import boto3
from botocore.exceptions import ClientError
import paho.mqtt.client as mqtt


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [FogNode] %(levelname)s: %(message)s"
)
logger = logging.getLogger("FogNode")

# --- Configuration via environment variables ---
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "mosquitto")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
DISPATCH_INTERVAL = float(os.getenv("DISPATCH_INTERVAL", "30"))  # seconds
HOUSE_ID = os.getenv("HOUSE_ID", "house_001")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "SensorReadings")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-1")

# --- DynamoDB setup ---
try:
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(DYNAMODB_TABLE)
    logger.info("DynamoDB table target: %s (region=%s)", DYNAMODB_TABLE, AWS_REGION)
except Exception as e:
    logger.error("Failed to initialise DynamoDB resource: %s", e)
    dynamodb = None
    table = None

# Anomaly thresholds per sensor type
ANOMALY_THRESHOLDS = {
    "temperature": {"min": 16.0, "max": 32.0},
    "humidity": {"min": 25.0, "max": 75.0},
    "co2": {"min": 350.0, "max": 1500.0},
    "pm25": {"min": 0.0, "max": 55.0},
}

# Stores raw readings per sensor type within the dispatch window
data_buffer = defaultdict(list)
buffer_lock = threading.Lock()


def on_connect(client, userdata, flags, rc, properties=None):
    """Subscribe to all sensor topics on connect."""
    logger.info("Connected to MQTT broker (rc=%s)", rc)
    client.subscribe("sensors/#", qos=1)
    logger.info("Subscribed to sensors/#")


def on_message(client, userdata, msg):
    """Buffer incoming sensor readings."""
    try:
        payload = json.loads(msg.payload.decode())
        sensor_type = payload.get("sensor_type", "unknown")
        value = payload.get("value")

        if value is None:
            logger.warning("Received message without 'value': %s", payload)
            return

        with buffer_lock:
            data_buffer[sensor_type].append({
                "value": value,
                "timestamp": payload.get("timestamp"),
                "unit": payload.get("unit", ""),
            })

        logger.debug(
            "Buffered %s reading: %.2f %s",
            sensor_type, value, payload.get("unit", ""),
        )
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Failed to parse message: %s — %s", msg.payload, e)


def filter_outliers(values: list[float]) -> list[float]:
    """Remove values outside 3 standard deviations from the mean."""
    if len(values) < 3:
        return values
    mean = statistics.mean(values)
    stdev = statistics.stdev(values)
    if stdev == 0:
        return values
    return [v for v in values if abs(v - mean) <= 3 * stdev]


def check_anomaly(sensor_type: str, avg_value: float) -> bool:
    """Check if the average value exceeds the anomaly threshold."""
    thresholds = ANOMALY_THRESHOLDS.get(sensor_type)
    if not thresholds:
        return False
    return avg_value < thresholds["min"] or avg_value > thresholds["max"]


def process_and_dispatch():
    """Process buffered data and dispatch to cloud"""
    with buffer_lock:
        if not data_buffer:
            logger.info("No data to dispatch this cycle")
            return

        # Copy and clear the buffer
        snapshot = dict(data_buffer)
        data_buffer.clear()

    processed_readings = []

    for sensor_type, readings in snapshot.items():
        raw_values = [r["value"] for r in readings]
        unit = readings[0]["unit"] if readings else ""

        # Filter outliers
        filtered = filter_outliers(raw_values)

        if not filtered:
            logger.warning("All %s readings were outliers, skipping", sensor_type)
            continue

        avg_value = statistics.mean(filtered)
        min_value = min(filtered)
        max_value = max(filtered)
        anomaly = check_anomaly(sensor_type, avg_value)

        processed = {
            "sensor_type": sensor_type,
            "avg_value": round(avg_value, 2),
            "min_value": round(min_value, 2),
            "max_value": round(max_value, 2),
            "unit": unit,
            "reading_count": len(raw_values),
            "filtered_count": len(filtered),
            "anomaly": anomaly,
            "house_id": HOUSE_ID,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        processed_readings.append(processed)

        status = "⚠️ ANOMALY" if anomaly else "✅ Normal"
        logger.info(
            "%s | %s: avg=%.2f %s (min=%.2f, max=%.2f) [%d readings]",
            status, sensor_type, avg_value, unit, min_value, max_value,
            len(raw_values),
        )

    if processed_readings:
        dispatch_to_cloud(processed_readings)


def dispatch_to_cloud(readings: list[dict]):
    """
    Dispatch processed readings to AWS DynamoDB.
    Each reading becomes an item keyed by device_sensor_id + timestamp.
    """
    if table is None:
        logger.error("DynamoDB table not initialised — skipping dispatch")
        return

    dispatch_time = datetime.now(timezone.utc).isoformat()
    logger.info(
        "DISPATCHING %d sensor types to DynamoDB table '%s'",
        len(readings), DYNAMODB_TABLE,
    )

    for reading in readings:
        item = {
            "device_sensor_id": f"{reading['house_id']}#{reading['sensor_type']}",
            "timestamp": reading["timestamp"],
            "sensor_type": reading["sensor_type"],
            "house_id": reading["house_id"],
            "avg_value": Decimal(str(reading["avg_value"])),
            "min_value": Decimal(str(reading["min_value"])),
            "max_value": Decimal(str(reading["max_value"])),
            "unit": reading["unit"],
            "reading_count": reading["reading_count"],
            "filtered_count": reading["filtered_count"],
            "anomaly": reading["anomaly"],
            "dispatch_time": dispatch_time,
        }

        try:
            table.put_item(Item=item)
            logger.info(
                "  ✅ Wrote %s reading to DynamoDB (device_sensor_id=%s)",
                reading["sensor_type"], item["device_sensor_id"],
            )
        except ClientError as e:
            logger.error(
                "DynamoDB write failed for %s: %s",
                reading["sensor_type"],
                e.response["Error"]["Message"],
            )
        except Exception as e:
            logger.error(
                "Unexpected error writing %s to DynamoDB: %s",
                reading["sensor_type"], e,
            )


def dispatch_loop():
    """Periodically process and dispatch buffered data."""
    logger.info("Dispatch loop started (interval=%.0fs)", DISPATCH_INTERVAL)
    while True:
        time.sleep(DISPATCH_INTERVAL)
        process_and_dispatch()


def main():
    logger.info("=== Fog Node Starting ===")
    logger.info("MQTT Broker: %s:%d", MQTT_BROKER_HOST, MQTT_BROKER_PORT)
    logger.info("Dispatch interval: %.0fs", DISPATCH_INTERVAL)
    logger.info("House ID: %s", HOUSE_ID)

    # Start dispatch loop in a background thread
    dispatch_thread = threading.Thread(target=dispatch_loop, daemon=True)
    dispatch_thread.start()

    # Connect to MQTT
    client = mqtt.Client(
        client_id=f"fog_node_{HOUSE_ID}",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )
    client.on_connect = on_connect
    client.on_message = on_message

    # Retry connection
    for attempt in range(1, 11):
        try:
            client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
            break
        except ConnectionRefusedError:
            wait = min(2 ** attempt, 30)
            logger.warning(
                "Connection attempt %d/10 failed. Retrying in %ds...",
                attempt, wait,
            )
            time.sleep(wait)
    else:
        logger.error("Could not connect to MQTT broker. Exiting.")
        return

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Fog node stopped by user")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
