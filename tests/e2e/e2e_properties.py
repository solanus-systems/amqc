#!/usr/bin/env micropython

"""End-to-end test for publish/subscribe functionality."""

import asyncio
import json
import logging
import os
import sys

from amqc.client import MQTTClient, config
from amqc.properties import (
    CONTENT_TYPE,
    CORRELATION_DATA,
    PAYLOAD_FORMAT_INDICATOR,
    PAYLOAD_FORMAT_UTF8,
    USER_PROPERTY,
)

# Set up logging; pass LOG_LEVEL=DEBUG if needed for local testing
logger = logging.getLogger()
logger.setLevel(getattr(logging, os.getenv("LOG_LEVEL", "WARNING").upper()))
formatter = logging.Formatter("%(asctime)s.%(msecs)d - %(levelname)s - %(name)s - %(message)s")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
logger.handlers = []
logger.addHandler(handler)
rx_logger = logging.getLogger("rx")
tx_logger = logging.getLogger("tx")

# MQTT Client config
config["server"] = "localhost"
config["queue_len"] = 1  # use event queue
tx_config = config.copy()
rx_config = config.copy()
tx_config["client_id"] = "tx"
rx_config["client_id"] = "rx"

# Set up MQTT clients
tx_client = MQTTClient(tx_config, logger=tx_logger)
rx_client = MQTTClient(rx_config, logger=rx_logger)

# Store received messages
messages_received = []


# Handler for received messages that logs and stores them
async def message_handler():
    async for topic, payload, _retained, properties in rx_client.queue:
        logger.debug(
            f"Received message '{payload.decode()}' on {topic.decode()} with properties {properties}"
        )
        messages_received.append((payload, properties))


# Simulate publishing messages with various MQTTv5 properties
async def publisher():
    # Send a message with binary correlation data
    await tx_client.publish(
        "test/topic",
        "Correlation data test".encode(),
        properties={CORRELATION_DATA: "my opaque value".encode()},
    )
    await asyncio.sleep(0.1)

    # Send a message with some arbitrary user properties
    await tx_client.publish(
        "test/topic",
        "User properties test".encode(),
        properties={
            USER_PROPERTY: {
                "key1": "value1",
            }
        },
    )
    await asyncio.sleep(0.1)

    # Use payload format and content-type to send a UTF-8 JSON payload
    await tx_client.publish(
        "test/topic",
        '{"key": "工"}'.encode("utf-8"),
        properties={
            PAYLOAD_FORMAT_INDICATOR: PAYLOAD_FORMAT_UTF8,
            CONTENT_TYPE: "application/json",
        },
    )
    await asyncio.sleep(0.1)


# Main test function
async def main():
    # Connect the clients
    await tx_client.connect()
    await rx_client.connect()

    # Subscribe and start the message handler
    await rx_client.subscribe("test/topic")
    asyncio.create_task(message_handler())

    # Simulate publishing messages with various MQTTv5 properties
    try:
        await publisher()
    # Handle any exceptions that occur during publishing
    except Exception:
        logger.exception("Error occurred while publishing messages", exc_info=True)
    # Ensure we disconnect the clients
    finally:
        await tx_client.disconnect()
        await rx_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

    # Ensure all messages were received
    assert (
        len(messages_received) == 3
    ), f"Expected 3 messages, got {len(messages_received)}"

    # Check the correlation data message
    corr_msg = messages_received[0]
    assert (
        corr_msg[0] == b"Correlation data test"
    ), f"Unexpected payload in correlation data message: {corr_msg[0].decode()}"
    assert (
        corr_msg[1][CORRELATION_DATA] == b"my opaque value"
    ), f"Unexpected correlation data: {corr_msg[1][CORRELATION_DATA]}"

    # Check the user properties message
    user_prop_msg = messages_received[1]
    assert (
        user_prop_msg[0] == b"User properties test"
    ), f"Unexpected payload in user properties message: {user_prop_msg[0].decode()}"
    assert user_prop_msg[1][USER_PROPERTY] == {
        "key1": "value1"
    }, f"Unexpected user properties: {user_prop_msg[1][USER_PROPERTY]}"

    # Check the UTF-8 JSON payload
    utf8_json_msg = messages_received[2]
    utf8_json_payload = utf8_json_msg[0].decode("utf-8")
    assert (
        utf8_json_payload == '{"key": "工"}'
    ), f"Unexpected payload in UTF-8 JSON message: {utf8_json_payload}"
    props = utf8_json_msg[1]
    assert (
        props[PAYLOAD_FORMAT_INDICATOR] == 1
    ), f"Unexpected PAYLOAD_FORMAT_INDICATOR: {props[PAYLOAD_FORMAT_INDICATOR]}"
    assert (
        props[CONTENT_TYPE] == "application/json"
    ), f"Unexpected CONTENT_TYPE: {props[CONTENT_TYPE]}"
    parsed_obj = json.loads(utf8_json_payload)
    assert parsed_obj == {"key": "工"}, f"Unexpected parsed JSON object: {parsed_obj}"

    print("\033[1m\tOK\033[0m")
