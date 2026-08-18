from utils import *
from pydantic.color import COLORS_BY_NAME
from constants import *

LOXONE_MAX_VAL_BRIGHTNESS = 100
MATTER_MAX_VAL_BRIGHTNESS = 255
RGB_WHITE = [255, 255, 255]
RGB_BLACK = [0, 0, 0]
COLOR_TEMP_WARM_WHITE_KELVIN = 2900
COLOR_TEMP_MIN_VALUE_KELVIN = 2800
COLOR_TEMP_MAX_VALUE_KELVIN = 6500


def loxone2matter_brightness(brightness):
    return int((brightness * MATTER_MAX_VAL_BRIGHTNESS) / LOXONE_MAX_VAL_BRIGHTNESS)


services_database = {
    "light": {
        "turn_on": lambda value: {"service": "turn_on", "service_data": {}},
        "turn_off": lambda value: {"service": "turn_off", "service_data": {}},
        "state": lambda value: {"service": "turn_on" if to_boolean(value) else "turn_off", "service_data": {}},
        "brightness": lambda value: {"service": "turn_on", "service_data": {"brightness": int(value * 2.55)}},
        "color_temp": lambda value: {"service": "turn_on",
                                     "service_data": {"color_temp_kelvin": convert_color_temp2kelvin(value)}},
        "color": lambda value: {"service": "turn_on", "service_data": {"rgb_color": value, "brightness": max(value)}}
    }
}


def handle_matter_service(domain, service, value):
    try:
        res = services_database[domain][service](value)
        return res.get("service", service), res.get("service_data", {})
    except Exception as e:
        return "no-service", {}


def compare_states(old_state, new_state):
    differences = {}
    for key, new_value in new_state.items():
        if key == "attributes" and isinstance(new_value, dict):
            old_attributes = old_state.get("attributes", {})
            attr_diff = {
                attr_key: value
                for attr_key, value in new_value.items()
                if attr_key not in old_attributes or old_attributes[attr_key] != value
            }
            if attr_diff:
                differences["attributes"] = attr_diff

        # compare of not being a key "attribute"
        elif key not in old_state or old_state[key] != new_value:
            differences[key] = new_value
    # filter some keys out
    keys_to_remove = ["last_reported", "last_updated", "context"]
    for key in keys_to_remove:
        differences.pop(key, None)

    attributes = differences.pop('attributes')
    return {**differences, **attributes}
