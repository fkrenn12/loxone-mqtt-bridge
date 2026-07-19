from pathlib import Path
import json

devices = {
    "kitchen_switch": "TS0044_2",
    "kitchen_window": "ZG-102ZA",
    "bath_window": "ZG-102ZA",
    "kitchen_plug": "A7Z",
    "lovely_flower_": "TS0601_soil_3",
    "bath_presence": "ZG-204ZH",
    "living_plug": "E22x4",
    "living_lamp": "HueWhite1600"
}

loxone = {
    "ip-address": "192.168.0.5",
    "udp-port": 4444
}

mqtt = {
    "HOST": "mosquitto",
    "PORT": 1883,
    "USERNAME": "",
    "PASSWORD": "",
    "SSL": "0",
    "LAST_CONNECTION_TIME": ""
}


def write_init_config_devices(path: Path):
    with open(path, "w") as f:
        f.write(json.dumps(devices, indent=4))


def write_init_config_loxone(path: Path):
    with open(path, "w") as f:
        f.write(json.dumps(loxone, indent=4))


def write_init_config_mqtt(path: Path):
    with open(path, "w") as f:
        f.write(json.dumps(mqtt, indent=4))
