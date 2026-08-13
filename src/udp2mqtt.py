from json import JSONDecodeError

from utils import *
from logger import logger
from config import config
from mqtt_node import fast_mqtt
from zigbee import handle_zigbee_service


def udp2mqtt(msg: str):
    # logger.info(f"Received UDP: {msg}")
    splitted = msg.split("/")
    if len(splitted) == 2:
        device_name = splitted[0]
        prop = None
        value = splitted[1]
    elif len(splitted) == 3:
        device_name = splitted[0]
        prop = splitted[1]
        value = splitted[2]
    else:
        logger.error(f"Invalid message format:{msg}")
        return

    if device_name == "ping":
        return

    try:
        device = config.devices.get(device_name)
        topic = device.get("topic", "")
    except:
        logger.error(f"No device {device_name} found.")
        return

    if prop is None:
        logger.error(f"Cannot process message - missing property: {msg}")
        return

    try:
        value = handle_zigbee_service(device, prop, value)
    except:
        # no valid model definition defined
        logger.error(f"Error handling zigbee device: {device} Property: {prop} Value: {value}")

    value = cast_to_numeric(value)

    # convert true/True and false/False to boolean
    if isinstance(value, str):
        value = {"true": True, "false": False}.get(value.lower(), value)

    try:
        value = json.loads(value)
    except:
        pass

    try:
        payload = {prop: value}
        json.dumps(payload)  # Verify if payload is serializable to JSON
    except (TypeError, JSONDecodeError) as e:
        logger.error(f"Invalid JSON data: {prop}:{value} - {e}")
        return

    if topic:
        topic = f"{topic}/set"
        logger.info(f"Publishing MQTT: {topic} {payload}")
        try:
            fast_mqtt.publish(topic, payload, qos=1)
        except:
            logger.error(f"Error publishing MQTT: {topic} {payload}")
