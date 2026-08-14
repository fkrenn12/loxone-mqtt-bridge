from utils import *
from config import config
from pydantic.color import COLORS_BY_NAME
from constants import *

LOXONE_MIN_VAL_BRIGHTNESS = 0
LOXONE_MAX_VAL_BRIGHTNESS = 100
RGB_WHITE = [255, 255, 255]
RGB_BLACK = [0, 0, 0]

services_database = {
    "turn_on":  {"state": True},
    "turn_off": {"state": False},
    "state": lambda value: {"state": value},
    "brightness": lambda value: {"brightness": int(value * 2.54)},
    "color_temp": lambda value: {"color_temp": value},
    "rgb": lambda value: {"color": {"rgb": ",".join(map(str, normalize_to_list(value)))},
                          "brightness": min(max(normalize_to_list(value)), 254)
                          },
    "color": lambda value: {"color": {"rgb": ",".join(map(str, loxone_color_code2rgb(loxone_color_code=value)))},
                            "brightness": min(loxone_color_code_maxvalue(loxone_color_code=value), 254)
                            },
    "color_by_name": lambda value: {"color": {"rgb": ",".join(map(str, value))},
                                    "brightness": min(max(value), 254)
                                    },
}

property_mappings = {"color_temp_percent": "color_temp"}


def handle_zigbee_service(device, prop, value):
    prop = property_mappings.get(prop, prop)
    # TODO: COLOR_BLACK wird nicht behandelt, wie bei matter
    if prop == "color_by_name":
        try:
            try:
                value = COLORS_BY_NAME[value]
            except:
                value = COLORS_BY_NAME_DE[value]
            value = list(value)
        except:
            return {}
    model_name = device["model_name"]
    model = next((m for m in config.definitions["definitions"] if m["definition(Zigbee2MQTT)"] == model_name), None)
    prop = model["default_expose"] if prop is None else prop
    # property limits and scaling
    if model:
        limits = model.get("limits", {})
        if prop in limits and is_castable_to_numeric(value):
            in_min = limits[prop].get("in_min", 0)
            in_max = limits[prop].get("in_max", 100)
            out_min = limits[prop].get("out_min", 0)
            out_max = limits[prop].get("out_max", 100)
            value = int(scale_and_clamp(int(value), in_min, in_max, out_min, out_max))

        value = apply_value_mapping(model, prop, value)
    value = cast_to_numeric(value)

    # convert true/True and false/False to boolean
    if isinstance(value, str):
        value = {"true": True, "false": False}.get(value.lower(), value)
    try:
        value = json.loads(value)
    except:
        pass

    try:
        x = services_database[prop](value)
        # print(x)
        return x
    except Exception as e:
        return {}
