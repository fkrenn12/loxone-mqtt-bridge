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


def convert2turnonoff(value):
    return "turn_on" if value else "turn_off"


services_database = {
    "light": {
        "turn_on": lambda value: {},
        "turn_off": lambda value: {},
        "state": lambda value: {},
        "brightness": lambda value: {"brightness": int(value * 2.55)},
        "color_temp": lambda value: {"color_temp_kelvin": convert_color_temp2kelvin(value)},
        "color": lambda value: {"rgb_color": value,
                                "brightness": max(value),
                                }
    }
}

service_mappings = {"light": {"turn_on": lambda value: "turn_on",
                              "turn_off": lambda value: "turn_off",
                              "state": lambda value: convert2turnonoff(value),
                              "brightness": lambda value: "turn_on",
                              "color_temp": lambda value: "turn_on",
                              "color": lambda value: "turn_on"}}


def handle_matter_service(domain, service, value):
    try:
        service_data = services_database[domain][service](value)
        # service = service_mappings.get(domain, {}).get(service, None)
        if service:
            service = service_mappings[domain][service](value)
    except Exception as e:
        service = "no-service"
        service_data = {}
    return service, service_data


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
