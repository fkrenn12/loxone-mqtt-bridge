from idlelib.debugobj_r import remote_object_tree_item
from pathlib import Path
import json
from typing import Any

COLOR_TEMP_MIN_VALUE_KELVIN = 2702
COLOR_TEMP_MAX_VALUE_KELVIN = 6500


def is_running_in_container():
    return Path('/run/.dockerenv').is_file() or Path('/.dockerenv').is_file()


def load_json_file(file_path: Path):
    with file_path.open('r', encoding="utf-8") as file:
        try:
            return json.loads(file.read())
        except json.decoder.JSONDecodeError:
            return dict()


def save_json_file(file_path: Path, json_dict: dict):
    with open(file_path, "w", encoding="utf-8") as f:
        try:
            json.dump(json_dict, fp=f, indent=4)
        except json.JSONDecodeError:
            return False


def is_castable_to_numeric(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def cast_to_numeric(value):
    if isinstance(value, str):
        try:
            return int(value) if value.isdigit() else float(value)
        except ValueError:
            pass
    return value


def scale_and_clamp(value, in_min, in_max, out_min, out_max):
    value = max(in_min, min(value, in_max))
    return out_min + (value - in_min) * (out_max - out_min) / (in_max - in_min)


def to_boolean(value):
    true_values = {"on", "true", "1", 1, True}
    false_values = {"off", "false", "0", 0, False}
    if isinstance(value, str):
        value = value.strip().lower()
    if value in true_values:
        return True
    elif value in false_values:
        return False
    else:
        raise ValueError(f"Invalid value: {value}")


def normalize_to_list(value: Any):
    input_str = str(value)
    try:
        # Replace round brackets with square brackets and clean the string
        cleaned = input_str.replace('(', '[').replace(')', ']').strip()
        # Safely evaluate the cleaned string as a Python list
        normalized_list = eval(cleaned)
        # Ensure the result is a list
        if isinstance(normalized_list, list):
            return normalized_list
        else:
            raise ValueError("Input could not be converted to a list.")
    except Exception as e:
        raise ValueError(f"Invalid input: {input_str}. Error: {e}")


def apply_value_mapping(model: dict, key: str, value: Any):
    _value = str(value).lower()
    mapping = model["value_mappings"].get(key)
    return mapping.get(_value, value) if mapping else value


def get_message_formats(model: dict, key: str):
    default_format = model.get("default_message_format", [])
    specific_format = model.get("specific_message_formats", {}).get(key)
    if isinstance(default_format, dict):
        default_format = [default_format]
    return specific_format if specific_format else default_format


def loxone_rgb_format_to_hue_sat(rgb_text):
    rgb = {item.split('=')[0]: float(item.split('=')[1][:-1]) / 100 for item in rgb_text.split(', ')}
    r, g, b = rgb['R'], rgb['G'], rgb['B']
    c_max = max(r, g, b)
    c_min = min(r, g, b)
    delta = c_max - c_min
    hue = 0
    if delta == 0:
        hue = 0
    elif c_max == r:
        hue = 60 * (((g - b) / delta) % 6)
    elif c_max == g:
        hue = 60 * (((b - r) / delta) + 2)
    elif c_max == b:
        hue = 60 * (((r - g) / delta) + 4)
    saturation = 0 if c_max == 0 else (delta / c_max) * 100
    return {"hue": hue, "sat": saturation}


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


def convert_color_temp2kelvin(value):
    if 0 <= value <= 100:
        # percent
        return int(COLOR_TEMP_MIN_VALUE_KELVIN + (COLOR_TEMP_MAX_VALUE_KELVIN - COLOR_TEMP_MIN_VALUE_KELVIN) * value / 100)
    elif 101 <= value <= 999:
        # mired
        return min(max(int(1000000 / value), COLOR_TEMP_MIN_VALUE_KELVIN), COLOR_TEMP_MAX_VALUE_KELVIN)
    elif 1000 <= value <= 10000:
        # kelvin
        return min(max(value, COLOR_TEMP_MIN_VALUE_KELVIN), COLOR_TEMP_MAX_VALUE_KELVIN)
    else:
        return 0


def convert_color_temp2mired(value):
    value = convert_color_temp2kelvin(value)
    if value > 0:
        return int(1000000 / value)
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
