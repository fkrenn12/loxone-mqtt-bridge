from pathlib import Path
import json
from typing import Any


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


def cast_to_numeric(value):
    if isinstance(value, str):
        try:
            return int(value) if value.isdigit() else float(value)
        except ValueError:
            pass
    return value


def to_boolean(value):
    """
    Wandelt den Eingabewert zuverlässig in einen booleschen Wert um.
    - Unterstützt: "True", "False", "0", "1", 0, 1, True, False.
    - Unsichere Konvertierungen wie eval() werden umgangen.
    """
    true_values = {"true", "1", 1, True}
    false_values = {"false", "0", 0, False}

    if isinstance(value, str):
        value = value.strip().lower()
    if value in true_values:
        return True
    elif value in false_values:
        return False
    else:
        raise ValueError(f"Invalid value: {value}")


def apply_value_mapping(model: dict, key: str, value: Any):
    value = str(value).lower()
    mapping = model["value_mappings"].get(key)
    return mapping.get(value, value) if mapping else value


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
