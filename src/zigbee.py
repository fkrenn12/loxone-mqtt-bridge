from utils import *
from config import config
from pydantic.color import COLORS_BY_NAME
from constants import *

LOXONE_MIN_VAL_BRIGHTNESS = 0
LOXONE_MAX_VAL_BRIGHTNESS = 100
RGB_WHITE = [255, 255, 255]
RGB_BLACK = [0, 0, 0]


def convert2onoff(value):
    return "ON" if value else "OFF"


services_database = {
    "turn_on": lambda value: {"state": "ON"},
    "turn_off": lambda value: {"state": "OFF"},
    "state": lambda value: {"state": convert2onoff(value)},
    "brightness": lambda value: {"brightness": min(int(value * 2.54), 254)},
    "color_temp": lambda value: {"color_temp": convert_color_temp2mired(value)},
    "color": lambda value: {"color": {"rgb": ",".join(map(str, value))},
                            "brightness": min(max(value), 254)
                            }
}


def handle_zigbee_service(device, service, value):
    device = config.devices.get(device)
    model_name = device["model_name"]
    model = next((m for m in config.definitions["definitions"] if m["definition(Zigbee2MQTT)"] == model_name), None)
    service = model["default_expose"] if service is None else service
    # service limits and scaling
    if model:
        limits = model.get("limits", {})
        if service in limits and is_castable_to_numeric(value):
            in_min = limits[service].get("in_min", 0)
            in_max = limits[service].get("in_max", 100)
            out_min = limits[service].get("out_min", 0)
            out_max = limits[service].get("out_max", 100)
            # if service != "brightness":
            #    value = int(scale_and_clamp(int(value), in_min, in_max, out_min, out_max))

        value = apply_value_mapping(model, service, value)

    # convert true/True and false/False to boolean
    if isinstance(value, str):
        value = {"true": True, "false": False}.get(value.lower(), value)
    try:
        value = json.loads(value)
    except:
        pass

    try:
        x = services_database[service](value)
        # print(x)
        return service, x
    except Exception as e:
        return service, {}
