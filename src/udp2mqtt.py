import json
from json import JSONDecodeError

from utils import *
from logger import logger
from config import config
from mqtt_node import fast_mqtt


def udp2mqtt(msg: str):
    # logger.info(f"Received UDP: {msg}")
    splitted = msg.split("/")
    if len(splitted) == 2:
        device_name = splitted[0]
        key = None
        value = splitted[1]
    elif len(splitted) == 3:
        device_name = splitted[0]
        key = splitted[1]
        value = splitted[2]
    else:
        logger.error(f"Invalid message format:{msg}")
        return
    try:
        device = config.devices.get(device_name)
        topic = device.get("topic", "")
    except:
        logger.error(f"No device {device_name} found.")
        return

    try:
        model_name = device["model_name"]
        model = next((m for m in config.definitions["definitions"] if m["name"] == model_name), None)
        key = model["default_expose"] if key is None else key
        value = apply_value_mapping(model, key, value)
    except:
        # no valid model definition defined
        logger.error(f"No information found modeling to UDP: {device}")
        if key is None:
            logger.error(f"Cannot process message - missing key: {msg}")
            return

    value = cast_to_numeric(value)

    # convert true/True and false/False to boolean
    if isinstance(value, str):
        value = {"true": True, "false": False}.get(value.lower(), value)

    try:
        payload = json.dumps({key: value})
    except JSONDecodeError:
        logger.error(f"Invalid JSON: {key}:{value}")
        return

    if topic:
        topic = f"{topic}/set"
        logger.info(f"Publishing MQTT: {topic} {payload}")
        try:
            fast_mqtt.publish(topic, payload, qos=1)
        except:
            logger.error(f"Error publishing MQTT: {topic} {payload}")
