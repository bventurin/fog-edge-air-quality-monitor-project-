# Fog and Edge CA Project


## Overview
This project simulates an IoT network of smart home air quality sensors (Temperature, Humidity, CO2, PM2.5). The sensors generate data that is published to a local MQTT broker (Mosquitto). A Fog Node edge appliance subscribes to these MQTT topics, buffers the data, filters outliers, checks for anomalies, and sends aggregated data to an AWS DynamoDB. A serverless dashboard (using AWS API Gateway and Lambda functions) then queries this data to provide a real-time web visualization.
The static web page is hosted in AWS S3. 

## Architecture
- **Sensors:** Python-based simulators running in Docker containers.
- **Edge Layer:** A Mosquitto MQTT broker and a custom Python Fog Node for local processing.
- **Cloud Backend:** AWS DynamoDB for storage, AWS Lambda for API logic.
- **Frontend Dashboard:** A serverless HTML/JS/CSS dashboard hosted in AWS S3.

## Running Locally
Requirements:
- Docker and Docker Compose
- Configured AWS Credentials (`~/.aws/credentials`)

To start the local sensor and fog environment:
```bash
docker compose up --build
```
