#!/usr/bin/env micropython

"""End-to-end test for keepalive and client disconnection functionality."""

import asyncio
import logging
import os
import sys

from amqc.client import MQTTClient, config

# Set up logging; pass LOG_LEVEL=DEBUG if needed for local testing
logger = logging.getLogger()
logger.setLevel(getattr(logging, os.getenv("LOG_LEVEL", "WARNING").upper()))
format_str = "%(asctime)s.%(msecs)03.0f - %(levelname)s - %(name)s - %(message)s"
formatter = logging.Formatter(format_str)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
logger.handlers = []
logger.addHandler(handler)
device_logger = logging.getLogger("device")
control_logger = logging.getLogger("control")

# Base config
config["server"] = "localhost"
config["queue_len"] = 1

# Device client config
device_config = config.copy()
device_config["client_id"] = "device"
device_config["keepalive"] = 2  # Set very short keepalive interval
device_config["will"] = (  # Will message on disconnect
    "test/topic",
    b"Last will message",
)

# Control client config
control_config = config.copy()
control_config["client_id"] = "control"
last_will_sent = asyncio.Event()

# Create the clients
device_client = MQTTClient(device_config, logger=device_logger)
control_client = MQTTClient(control_config, logger=control_logger)

# Force the device client to ping slower than the keepalive interval, so
# the broker will disconnect it
device_client._ping_interval = 20000


# Handler to check last will message
async def message_handler():
    async for topic, payload, _retained, _properties in control_client.queue:
        logger.debug(f"Received message on {topic}: {payload.decode()}")
        if topic == "test/topic" and payload.decode() == "Last will message":
            last_will_sent.set()


async def main():
    # Connect both clients
    await device_client.connect()
    await control_client.connect()

    # Subscribe to the last will topic and system topic
    await control_client.subscribe("test/topic")
    asyncio.create_task(message_handler())

    # Wait to receive the last will message
    await asyncio.wait_for(last_will_sent.wait(), timeout=30)


if __name__ == "__main__":
    asyncio.run(main())
    print("\033[1m\tOK\033[0m")
