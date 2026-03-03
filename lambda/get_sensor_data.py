"""
Lambda function — returns sensor time-series data from DynamoDB.

API Gateway route: GET /api/sensor/{sensor_type}?hours=1
"""

import json
import os
import boto3
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from boto3.dynamodb.conditions import Key

DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "SensorReadings")
HOUSE_ID = os.environ.get("HOUSE_ID", "house_001")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)

VALID_SENSORS = ["temperature", "humidity", "co2", "pm25"]


def decimal_to_float(obj):
    """Convert Decimal values so json works"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def lambda_handler(event, context):
    # Get sensor type from the URL path
    sensor_type = event.get("pathParameters", {}).get("sensor_type", "")
    if sensor_type not in VALID_SENSORS:
        return {
            "statusCode": 404,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Unknown sensor type"}),
        }

    # Get hours from query string
    params = event.get("queryStringParameters") or {}
    try:
        hours = int(params.get("hours", "1"))
        if hours < 1 or hours > 168:  # Max 1 week
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "hours must be between 1 and 168"}),
            }
    except ValueError:
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "hours must be a valid integer"}),
        }

    # Query DynamoDB
    device_sensor_id = f"{HOUSE_ID}#{sensor_type}"
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    response = table.query(
        KeyConditionExpression=(
            Key("device_sensor_id").eq(device_sensor_id)
            & Key("timestamp").gte(since)
        ),
        ScanIndexForward=True,
    )
    items = response.get("Items", [])

    while "LastEvaluatedKey" in response:
        response = table.query(
            KeyConditionExpression=(
                Key("device_sensor_id").eq(device_sensor_id)
                & Key("timestamp").gte(since)
            ),
            ExclusiveStartKey=response["LastEvaluatedKey"],
            ScanIndexForward=True,
        )
        items.extend(response.get("Items", []))

    return {
        "statusCode": 200,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": json.dumps(items, default=decimal_to_float),
    }
