#!/usr/bin/env micropython

"""End-to-end test for publish/subscribe functionality."""

import asyncio
import logging
import os
import sys

from amqc.client import MQTTClient
from amqc.client import config as mqtt_settings

# Set up logging; pass LOG_LEVEL=DEBUG if needed for local testing
logger = logging.getLogger()
logger.setLevel(getattr(logging, os.getenv("LOG_LEVEL", "ERROR").upper()))
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
logger.handlers = []
logger.addHandler(handler)

# MQTT Client config
mqtt_settings["server"] = "localhost"
mqtt_settings["queue_len"] = 1  # use event queue
device_mqtt_settings = mqtt_settings.copy()
control_mqtt_settings = mqtt_settings.copy()
device_mqtt_settings["client_id"] = "device"
control_mqtt_settings["client_id"] = "server"

# Set up MQTT clients
device_client = MQTTClient(device_mqtt_settings)
control_client = MQTTClient(control_mqtt_settings)

# Store received messages
device_received = []
control_received = []


# Handler for device messages that logs and stores them
async def device_handler():
    async for topic, payload, _retained, _properties in device_client.queue:
        logger.debug(f"Device received {len(payload)} bytes on {topic.decode()}: {payload.decode()}")
        device_received.append(payload)


# Handler for control messages that logs and stores them
async def control_handler():
    async for topic, payload, _retained, _properties in control_client.queue:
        logger.debug(f"Control received {len(payload)} bytes on {topic.decode()}: {payload.decode()}")
        control_received.append(payload)


# Simulate publishing messages from device
async def device_publisher():
    for i in range(3):
        await device_client.publish("/control", f"Device message {i}".encode())
        logger.debug(f"Device published message {i} to /control")
        await asyncio.sleep(0.1)  # Simulate some delay between messages


# Simulate publishing messages from control
async def control_publisher():
    for i in range(3):
        await control_client.publish("/device", f"Control message {i}".encode())
        logger.debug(f"Control published message {i} to /device")
        await asyncio.sleep(0.1)  # Simulate some delay between messages


# Main test function
async def main():
    # Connect both clients
    await device_client.connect(True)
    logger.debug("Device client connected")
    await control_client.connect(True)
    logger.debug("Control client connected")

    # Subscribe to topics
    await device_client.subscribe("/device")
    logger.debug("Device client subscribed to /device")
    await control_client.subscribe("/control")
    logger.debug("Control client subscribed to /control")

    # Run handlers in the background
    asyncio.create_task(device_handler())
    asyncio.create_task(control_handler())

    # Run publishers in the foreground
    await device_publisher()
    await control_publisher()

    # Disconnect and clean up
    await device_client.disconnect()
    logger.debug("Device client disconnected")
    await control_client.disconnect()
    logger.debug("Control client disconnected")


if __name__ == "__main__":
    asyncio.run(main())

    # Ensure all messages were received
    assert (
        len(device_received) == 3
    ), f"Device received {len(device_received)} messages, expected 3"
    assert (
        len(control_received) == 3
    ), f"Control received {len(control_received)} messages, expected 3"
    for i in range(3):
        assert (
            device_received[i] == f"Control message {i}".encode()
        ), f"Expected Control message {i}, got {device_received[i]}"
        assert (
            control_received[i] == f"Device message {i}".encode()
        ), f"Expected Device message {i}, got {control_received[i]}"

    print("\033[1m\tOK\033[0m")
