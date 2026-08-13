LOXONE_MAX_VAL_BRIGHTNESS = 100
MATTER_MAX_VAL_BRIGHTNESS = 255
RGB_WHITE = [255, 255, 255]
RGB_BLACK = [0, 0, 0]
COLOR_TEMP_WARM_WHITE_KELVIN = 2900
COLOR_TEMP_MIN_VALUE_KELVIN = 2800
COLOR_TEMP_MAX_VALUE_KELVIN = 6500
DEFAULT_BRIGHTNESS = 125


def loxone_color_code_maxvalue(loxone_color_code):
    red, green, blue = extract_rgb_components(loxone_color_code)
    return int(max(red, green, blue))


def loxone_color_code2rgb(loxone_color_code):
    red, green, blue = extract_rgb_components(loxone_color_code)
    max_value = max(red, green, blue)
    if not max_value:
        return [0, 0, 0]
    factor = 255 / max_value
    red *= factor
    green *= factor
    blue *= factor
    return [int(red), int(green), int(blue)]


def loxone_color_temp_percent2color_temp_kelvin(percent):
    if percent > 0:
        return int(
            COLOR_TEMP_MIN_VALUE_KELVIN + (COLOR_TEMP_MAX_VALUE_KELVIN - COLOR_TEMP_MIN_VALUE_KELVIN) * percent / 100)
    else:
        return 0


def extract_rgb_components(color_code):
    blue = (color_code // 1000000) / 100
    green = (color_code // 1000 % 1000) / 100
    red = (color_code % 1000) / 100
    blue = min(int(blue * 255), 255)
    green = min(int(green * 255), 255)
    red = min(int(red * 255), 255)
    return red, green, blue


def loxone2matter_brightness(brightness):
    return int((brightness * MATTER_MAX_VAL_BRIGHTNESS) / LOXONE_MAX_VAL_BRIGHTNESS)


services_database = {
    "light": {
        "turn_on": {},
        "turn_off": {},
        "brightness": lambda value: {"brightness": loxone2matter_brightness(value)},
        "color_temp_kelvin": lambda value: {"color_temp_kelvin": value},
        "color_temp": lambda value: {"color_temp_kelvin": value},
        "color_temp_percent": lambda value: {"color_temp_kelvin": loxone_color_temp_percent2color_temp_kelvin(value)},
        "rgb": lambda value: {"rgb_color": loxone_color_code2rgb(loxone_color_code=value),
                              "brightness": loxone_color_code_maxvalue(loxone_color_code=value),
                              },
        "color": lambda value: {"rgb_color": loxone_color_code2rgb(loxone_color_code=value),
                                "brightness": loxone_color_code_maxvalue(loxone_color_code=value),
                                }
    }
}

service_mappings = {"light": {"turn_on": "turn_on",
                              "turn_off": "turn_off",
                              "brightness": "turn_on",
                              "color_temp_kelvin": "turn_on",
                              "color_temp": "turn_on",
                              "color_temp_percent": "turn_on",
                              "color": "turn_on",
                              "rgb": "turn_on"}}


def convert_rgbwhite_to_color_temp(service, service_data):
    return "turn_on", {"color_temp_kelvin": COLOR_TEMP_WARM_WHITE_KELVIN, "brightness": DEFAULT_BRIGHTNESS}


def handle_matter_service(domain, service, value):
    try:
        # we do not handle black rgb value, because in this case color_temp_kelvin will define the light
        is_black = loxone_color_code2rgb(value) == RGB_BLACK
        if service in {"rgb", "color"} and domain == "light" and is_black:
            raise Exception()
        service_data = services_database[domain][service](value)
        service = service_mappings.get(domain, {}).get(service, service)
    except Exception:
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
