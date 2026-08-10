from utils import loxone_rgb_format_to_hue_sat
from utils import decode_loxone_color_to_rgb, decode_loxone_color_to_brightness, convert_brightness

services_database = {
    "light": {
        "turn_on": {},
        "turn_off": {},
        "brightness": lambda value: {"brightness": convert_brightness(value)},
        "color_temp_kelvin": lambda value: {"color_temp_kelvin": value},
        "rgb": lambda value: {"rgb_color": decode_loxone_color_to_rgb(value),
                              "brightness": decode_loxone_color_to_brightness(value),
                              },
        "color": lambda value: {"rgb_color": decode_loxone_color_to_rgb(value),
                                "brightness": decode_loxone_color_to_brightness(value),
                                }
    }
}

service_switch = {"light": {"brightness": "turn_on",
                            "color_temp_kelvin": "turn_on",
                            "color": "turn_on",
                            "rgb": "turn_on"}}


def handle_matter_service(domain, service, value):
    try:
        service_data = services_database[domain][service](value)
        if value >= 100100100:
            service_data = {"color_temp_kelvin": 2702, "brightness": 125}
            service = "turn_on"
    except:
        service_data = {}

    service = service_switch.get(domain, {}).get(service, service)
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
