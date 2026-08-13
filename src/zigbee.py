from utils import *
from config import config

LOXONE_MIN_VAL_BRIGHTNESS = 0
LOXONE_MAX_VAL_BRIGHTNESS = 100
RGB_WHITE = [255, 255, 255]
RGB_BLACK = [0, 0, 0]


def handle_zigbee_service(device, prop, value):
    model_name = device["model_name"]
    model = next((m for m in config.definitions["definitions"] if m["definition(Zigbee2MQTT)"] == model_name), None)
    prop = model["default_expose"] if prop is None else prop
    # prop limits and scaling
    limits = model.get("limits", {})
    if prop in limits and is_castable_to_numeric(value):
        in_min = limits[prop].get("in_min", 0)
        in_max = limits[prop].get("in_max", 100)
        out_min = limits[prop].get("out_min", 0)
        out_max = limits[prop].get("out_max", 100)
        value = int(scale_and_clamp(int(value), in_min, in_max, out_min, out_max))
    value = apply_value_mapping(model, prop, value)
    return value
