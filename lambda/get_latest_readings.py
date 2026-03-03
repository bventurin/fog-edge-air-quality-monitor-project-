"""
Lambda function — returns the latest reading for each sensor from DynamoDB.

API Gateway route: GET /api/latest
"""

import json
import os
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key

DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "SensorReadings")
HOUSE_ID = os.environ.get("HOUSE_ID", "house_001")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)

VALID_SENSORS = ["temperature", "humidity", "co2", "pm25"]


def decimal_to_float(obj):
    """Convert Decimal values so json.dumps works."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def lambda_handler(event, context):
    result = {}

    for sensor_type in VALID_SENSORS:
        device_sensor_id = f"{HOUSE_ID}#{sensor_type}"

        response = table.query(
            KeyConditionExpression=Key("device_sensor_id").eq(device_sensor_id),
            ScanIndexForward=False, 
            Limit=1,
        )
        items = response.get("Items", [])
        result[sensor_type] = items[0] if items else None

    return {
        "statusCode": 200,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": json.dumps(result, default=decimal_to_float),
    }
