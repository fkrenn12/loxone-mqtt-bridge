from pathlib import Path
import json


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
