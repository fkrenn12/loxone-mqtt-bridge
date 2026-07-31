from utils import *
from config import config
from logger import logger


def mqtt2udp(topic: str, payload: dict):
    send = []
    device_name = topic.split("/")[-1]
    try:
        device = config.devices.get(device_name)
        model_name = device["model_name"]
        model = next((m for m in config.definitions["definitions"] if m["definition(Zigbee2MQTT)"] == model_name), None)
        exposes = model["exposes"]
        for key in exposes:
            value = payload.get(key, None)
            is_default_key = model.get("default_expose", "") == key
            if value is not None:
                value = str(value).lower()
                value = apply_value_mapping(model, key, value)

                message_formats = get_message_formats(model, key)
                for message_format in message_formats:
                    topic = device_name if is_default_key else f"{device_name}/{key}"
                    send.append(message_format.format(topic=topic, value=value))
    except:
        logger.info(f"No information found for device: {device_name}")
        for key in payload.keys():
            value = payload.get(key)
            # convert true/false and on/off into 1 and 0
            if isinstance(value, bool):
                value = int(value)
            elif isinstance(value, str) and value.lower() in ["on", "off"]:
                value = 1 if value.lower() == "on" else 0

            send.append(f"{device_name}/{key}/{value}")

    return send
    # return []
