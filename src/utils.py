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


def to_int_or_float_if_possible(value):
    try:
        # If the value is a string, check if it can be converted to a number
        if isinstance(value, str):
            # Check if it can be converted to an integer
            if value.isdigit():
                return int(value)
            # Check if it can be converted to a float
            try:
                return float(value)
            except ValueError:
                pass
        # Return the original value if not convertible
        return value
    except Exception as e:
        return value


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
