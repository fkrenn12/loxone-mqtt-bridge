from utils import decode_loxone_color_to_rgb, decode_loxone_color_to_brightness
RGB_WHITE = [255, 255, 255]
COLOR_TEMP_WARM_WHITE = 2900
DEFAULT_BRIGHTNESS = 125
services_database = {
    "light": {
        "turn_on": {},
        "turn_off": {},
        "brightness": lambda value: {"brightness": int(value * 2.55), "color_temp_kelvin": 2702},
        "color_temp_kelvin": lambda value: {"color_temp_kelvin": value},
        "color_temp": lambda value: {"color_temp_kelvin": value},
        "rgb": lambda value: {"rgb_color": decode_loxone_color_to_rgb(value),
                              "brightness": decode_loxone_color_to_brightness(value),
                              },
        "color": lambda value: {"rgb_color": decode_loxone_color_to_rgb(value),
                                "brightness": decode_loxone_color_to_brightness(value),
                                }
    }
}

service_mappings = {"light": {"turn_on": "turn_on",
                              "turn_off": "turn_off",
                              "brightness": "turn_on",
                              "color_temp_kelvin": "turn_on",
                              "color_temp": "turn_on",
                              "color": "turn_on",
                              "rgb": "turn_on"}}


def convert_white_to_color_temp(service, service_data):
    return "turn_on", {"color_temp_kelvin": COLOR_TEMP_WARM_WHITE, "brightness": DEFAULT_BRIGHTNESS}


def handle_matter_service(domain, service, value):
    try:
        if domain == "light" and service in {"rgb", "color"} and decode_loxone_color_to_rgb(value) == RGB_WHITE:
            return convert_white_to_color_temp(service, {})
        service_data = services_database[domain][service](value)
    except Exception:
        service_data = {}

    service = service_mappings.get(domain, {}).get(service, service)
    return service, service_data


'''
def handle_matter_service(domain, service, value):
    service_data = {}
    try:
        if domain == "light" and (service == "rgb" or service == "color") and decode_loxone_color_to_rgb(value) == [255, 255, 255]:
            service, service_data = replace_white_with_color_temp(service, service_data)
        else:
            service_data = services_database[domain][service](value)
    except:
        pass

    service = service_mappings.get(domain, {}).get(service, service)
    return service, service_data
'''


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
