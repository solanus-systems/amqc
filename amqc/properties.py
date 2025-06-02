"""
Property handling for MQTTv5. Adapted from:
https://github.com/peterhinch/micropython-mqtt/blob/master/mqtt_as/mqtt_v5_properties.py
"""

import struct

# Properties available in MQTTv5; see:
# https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901027
PAYLOAD_FORMAT_INDICATOR = 0x01
MESSAGE_EXPIRY_INTERVAL = 0x02
CONTENT_TYPE = 0x03
RESPONSE_TOPIC = 0x08
CORRELATION_DATA = 0x09
SUBSCRIPTION_IDENTIFIER = 0x0B
SESSION_EXPIRY_INTERVAL = 0x11
ASSIGNED_CLIENT_IDENTIFIER = 0x12
SERVER_KEEP_ALIVE = 0x13
AUTHENTICATION_METHOD = 0x15
AUTHENTICATION_DATA = 0x16
REQUEST_PROBLEM_INFORMATION = 0x17
WILL_DELAY_INTERVAL = 0x18
REQUEST_RESPONSE_INFORMATION = 0x19
RESPONSE_INFORMATION = 0x1A
SERVER_REFERENCE = 0x1C
REASON_STRING = 0x1F
RECEIVE_MAXIMUM = 0x21
TOPIC_ALIAS_MAXIMUM = 0x22
TOPIC_ALIAS = 0x23
MAXIMUM_QOS = 0x24
RETAIN_AVAILABLE = 0x25
USER_PROPERTY = 0x26
MAXIMUM_PACKET_SIZE = 0x27
WILDCARD_SUBSCRIPTION_AVAILABLE = 0x28
SUBSCRIPTION_IDENTIFIERS_AVAILABLE = 0x29
SHARED_SUBSCRIPTION_AVAILABLE = 0x2A

# Indicates payload is UTF-8 encoded; pair with CONTENT_TYPE as a MIME type:
# 
# {
#     PAYLOAD_FORMAT_INDICATOR: PAYLOAD_FORMAT_UTF8,
#     CONTENT_TYPE: "application/json",
# }
PAYLOAD_FORMAT_UTF8 = bytes([1])    # 0x01


def encode_byte(value):
    # It takes in a byte and returns a byte
    return value


def encode_two_byte_int(value):
    return struct.pack("!H", value)


def encode_four_byte_int(value):
    return struct.pack("!I", value)


def encode_string(value):
    value = value.encode("utf-8")
    return struct.pack("!H", len(value)) + value


def encode_string_pair(value):
    # just get the first key and value
    key, value = list(value.items())[0]
    return encode_string(key) + encode_string(value)


def encode_binary(value):
    return struct.pack("!H", len(value)) + value


def encode_variable_byte_int(value):
    out = bytearray(4)
    i = 0
    for i in range(4):
        b = value & 0x7F
        value >>= 7
        if value > 0:
            b |= 0x80
        out[i] = b
        if value == 0:
            break
    return out[: i + 1]


# This table does not contain all properties (unlike the decode table)
# as not all properties can be sent by the client.
ENCODE_TABLE = {
    PAYLOAD_FORMAT_INDICATOR: encode_byte,
    MESSAGE_EXPIRY_INTERVAL: encode_four_byte_int,
    CONTENT_TYPE: encode_string,
    RESPONSE_TOPIC: encode_string,
    CORRELATION_DATA: encode_binary,
    SUBSCRIPTION_IDENTIFIER: encode_variable_byte_int,
    SESSION_EXPIRY_INTERVAL: encode_four_byte_int,
    AUTHENTICATION_METHOD: encode_string,
    AUTHENTICATION_DATA: encode_binary,
    REQUEST_PROBLEM_INFORMATION: encode_byte,
    WILL_DELAY_INTERVAL: encode_four_byte_int,
    REQUEST_RESPONSE_INFORMATION: encode_byte,
    SERVER_REFERENCE: encode_string,
    REASON_STRING: encode_string,
    RECEIVE_MAXIMUM: encode_two_byte_int,
    TOPIC_ALIAS_MAXIMUM: encode_two_byte_int,
    TOPIC_ALIAS: encode_two_byte_int,
    USER_PROPERTY: encode_string_pair,
    MAXIMUM_PACKET_SIZE: encode_four_byte_int,
}


def encode_properties(properties: dict):
    # If properties are empty or None, we can just return a single byte (0)
    if properties in (None, {}):
        return bytes(1)

    # We can't modify the properties dict, as user might want to use it later
    # So we will create a new dict with the encoded values.
    # This causes a slight increase in memory usage. But this is acceptable.
    pre_encoded_properties = {}

    # We keep track of the length of the properties
    properties_length = 0

    # Preprocess properties to encode everything as bytes.
    for key, value in properties.items():
        encode_func = ENCODE_TABLE.get(key)
        if encode_func is None:
            # We can just leave that data as is and assume that it is valid.
            tmp_value = value
        else:
            tmp_value = encode_func(value)
        pre_encoded_properties[key] = tmp_value

        # Pre-calculate the length of the properties
        properties_length += 1  # key
        properties_length += len(tmp_value)

    # Mark properties as deleted
    del properties

    variable_length = 1
    if properties_length > 127:
        variable_length += 1
    if properties_length > 16383:
        variable_length += 1
    if properties_length > 2097151:
        variable_length += 1

    # Now we can allocate the byte array
    properties_bytes = bytearray(variable_length + properties_length)
    view = memoryview(properties_bytes)

    i = 0
    while properties_length > 0x7F:
        view[i] = (properties_length & 0x7F) | 0x80
        properties_length >>= 7
        i += 1

    view[i] = properties_length
    i += 1

    for key, value in pre_encoded_properties.items():
        view[i] = key
        i += 1
        view[i : i + len(value)] = value
        i += len(value)

    return properties_bytes


def decode_byte(props, offset):
    value = props[offset]
    offset += 1
    return value, offset


def decode_two_byte_int(props, offset):
    value = struct.unpack_from("!H", props, offset)[0]
    offset += 2
    return value, offset


def decode_four_byte_int(props, offset):
    value = struct.unpack_from("!I", props, offset)[0]
    offset += 4
    return value, offset


def decode_string(props, offset):
    str_length = struct.unpack_from("!H", props, offset)[0]
    offset += 2
    value = props[offset : offset + str_length].decode("utf-8")
    offset += str_length
    return value, offset


def decode_string_pair(props, offset):
    key, offset = decode_string(props, offset)
    value, offset = decode_string(props, offset)
    item = {key: value}
    return item, offset


def decode_binary(props, offset):
    data_length = struct.unpack_from("!H", props, offset)[0]
    offset += 2
    value = props[offset : offset + data_length]
    offset += data_length
    return value, offset


def decode_variable_byte_int(props, offset):
    value = 0
    for i in range(4):
        b = props[offset]
        value |= (b & 0x7F) << (7 * i)
        offset += 1
        if not b & 0x80:
            break
    return value, offset


decode_property_lookup = {
    PAYLOAD_FORMAT_INDICATOR: decode_byte,
    MESSAGE_EXPIRY_INTERVAL: decode_four_byte_int,
    CONTENT_TYPE: decode_string,
    RESPONSE_TOPIC: decode_string,
    CORRELATION_DATA: decode_binary,
    SUBSCRIPTION_IDENTIFIER: decode_variable_byte_int,
    SESSION_EXPIRY_INTERVAL: decode_four_byte_int,
    ASSIGNED_CLIENT_IDENTIFIER: decode_string,
    SERVER_KEEP_ALIVE: decode_two_byte_int,
    AUTHENTICATION_METHOD: decode_string,
    AUTHENTICATION_DATA: decode_binary,
    REQUEST_PROBLEM_INFORMATION: decode_byte,
    WILL_DELAY_INTERVAL: decode_four_byte_int,
    REQUEST_RESPONSE_INFORMATION: decode_byte,
    RESPONSE_INFORMATION: decode_string,
    SERVER_REFERENCE: decode_string,
    REASON_STRING: decode_string,
    RECEIVE_MAXIMUM: decode_two_byte_int,
    TOPIC_ALIAS_MAXIMUM: decode_two_byte_int,
    TOPIC_ALIAS: decode_two_byte_int,
    MAXIMUM_QOS: decode_byte,
    RETAIN_AVAILABLE: decode_byte,
    USER_PROPERTY: decode_string_pair,
    MAXIMUM_PACKET_SIZE: decode_four_byte_int,
    WILDCARD_SUBSCRIPTION_AVAILABLE: decode_byte,
    SUBSCRIPTION_IDENTIFIERS_AVAILABLE: decode_byte,
    SHARED_SUBSCRIPTION_AVAILABLE: decode_byte,
}


def decode_properties(props, properties_length):
    if isinstance(props, memoryview):
        props = bytes(props)  # If a memoryview is passed, make a copy
    offset = 0
    properties = {}

    while offset < properties_length:
        property_identifier = props[offset]
        offset += 1

        if property_identifier in decode_property_lookup:
            decode_function = decode_property_lookup[property_identifier]
            value, offset = decode_function(props, offset)
            properties[property_identifier] = value
        else:
            raise ValueError(f"Unknown property identifier: {property_identifier}")

    return properties
