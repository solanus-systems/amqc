"""End-to-end test for MQTTS support."""

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

# Base config
config["server"] = "localhost"
config["queue_len"] = 1

# Device client config
# For editing the user/pass, see:
# https://mosquitto.org/documentation/authentication-methods/
device_config = config.copy()
device_config["client_id"] = "device"
device_config["user"] = "device"
device_config["password"] = "my_password"
device_config["ssl"] = True  # Enable SSL; should select port 8883
device_client = MQTTClient(device_config, logger=device_logger)


# Simulate publishing messages from device
async def device_publisher():
    for i in range(3):
        await device_client.publish("/control", f"Device message {i}".encode())
        logger.debug(f"Device published message {i} to /control")
        await asyncio.sleep(0.1)  # Simulate some delay between messages


async def main():
    # FIXME: in CI this throws ECONNREFUSED during SSL connection
    if os.getenv("CI") == "true":
        print("\033[1m\tSKIP\033[0m")
        return

    # Connect the device client
    await device_client.connect()

    # Start the publisher
    await device_publisher()

    # Wait for a short time to ensure messages are sent
    await asyncio.sleep(1)

    # Force a reconnection where the socket still exists
    device_client._connect_socket()

    print("\033[1m\tOK\033[0m")


if __name__ == "__main__":
    asyncio.run(main())
