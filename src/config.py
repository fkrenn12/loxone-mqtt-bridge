import os
import requests
from constants import *
from utils import *
from logger import logger
import time
from fastapi_mqtt import MQTTConfig
import ssl
import schedule
import threading

UDP_PORT = int(os.environ.get('UDP_PORT'))
UDP_PORT = UDP_PORT if UDP_PORT else UDP_DEFAULT_PORT
API_PORT = int(os.environ.get('API_PORT'))
API_PORT = API_PORT if API_PORT else API_DEFAULT_PORT

HOST_IP = os.environ.get('HOST_IP', None)
LOXONE_IP = os.environ.get('LOXONE_IP', None)
MQTT_HOST = os.environ.get('MQTT_HOST', None)
MQTT_PORT = os.environ.get('MQTT_PORT', None)
MQTT_USER = os.environ.get('MQTT_USER', None)
MQTT_PASS = os.environ.get('MQTT_PASS', None)
MQTT_SSL = to_boolean(os.environ.get('MQTT_SSL')) if os.environ.get('MQTT_SSL') else False
DOWNLOAD_URL_DEFINITIONS = os.environ.get('DOWNLOAD_URL_DEFINITIONS') or DEFAULT_DOWNLOAD_URL_DEFINITIONS
DEFINITIONS_UPDATE_INTERVAL_MIN = int(os.environ.get("DEFINITIONS_UPDATE_INTERVAL_MIN", "0") or 0)


print(">" * 100)
print("Environment variables:")
print(">" * 100)
print(f"DOWNLOAD_URL_DEFINITIONS: {DOWNLOAD_URL_DEFINITIONS}")
print(f"UDP_PORT: {UDP_PORT}")
print(f"API_PORT: {API_PORT}")
print(f"LOXONE_IP: {LOXONE_IP}")
print(f"MQTT_HOST: {MQTT_HOST}")
print(f"MQTT_PORT: {MQTT_PORT}")
print(f"MQTT_USER: {MQTT_USER}")
print(f"MQTT_PASS: {MQTT_PASS}")
print(f"MQTT_SSL: {MQTT_SSL}")
print("<" * 100)

CONFIG_PATH = Path("../config")
MQTT_CONFIG_FILE_PATH = Path(f"{CONFIG_PATH}/mqtt.json")
DEFINITIONS_CONFIG_FILE_PATH = Path(f"{CONFIG_PATH}/definitions.json")
LOXONE_CONFIG_FILE_PATH = Path(f"{CONFIG_PATH}/loxone.json")


class Config:
    def __init__(self, update_interval_minutes: int = 0):
        self.stop_scheduler = False
        self.devices = {}
        self.loxone = {}
        self.mqtt = MQTTConfig()
        self.definitions = {}
        if update_interval_minutes:
            logger.info(f"Start update definitions scheduler with interval of {update_interval_minutes} minutes.")
            schedule.every(update_interval_minutes).minutes.do(self.load_definitions)
        else:
            logger.info(f"Update definitions scheduler is disabled.")
        self.scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.scheduler_thread.start()

    def run_scheduler(self):
        while not self.stop_scheduler:
            schedule.run_pending()
            time.sleep(1)

    def stop(self):
        self.stop_scheduler = True
        logger.info("Scheduler stopped.")
        if self.scheduler_thread.is_alive():
            self.scheduler_thread.join()  # Warten, bis der Thread endet
            logger.info("Scheduler thread has been joined.")

    def load_mqtt(self):
        try:
            _mqtt = load_json_file(MQTT_CONFIG_FILE_PATH)
        except:
            _mqtt = {"host": f"{MQTT_DEFAULT_HOST}", "port": f"{MQTT_DEFAULT_PORT}",
                     "username": "", "password": "", "ssl": "0"}

        # override with environment settings and save to file
        _mqtt["host"] = MQTT_HOST if MQTT_HOST else _mqtt["host"]
        _mqtt["port"] = MQTT_PORT if MQTT_PORT else _mqtt["port"]
        _mqtt["username"] = MQTT_USER if MQTT_USER else _mqtt["username"]
        _mqtt["password"] = MQTT_PASS if MQTT_PASS else _mqtt["password"]
        _mqtt["ssl"] = MQTT_SSL if MQTT_SSL else to_boolean(_mqtt["ssl"])
        save_json_file(MQTT_CONFIG_FILE_PATH, _mqtt)

        self.mqtt.host = _mqtt.get("host")
        self.mqtt.port = int(_mqtt.get("port"))
        self.mqtt.keepalive = 60
        self.mqtt.username = _mqtt.get("username", str())
        self.mqtt.password = _mqtt.get("password", str())
        self.mqtt.reconnect_delay = 10
        self.mqtt.reconnect_retries = 200000
        # allow self signed certificates
        self.mqtt.ssl = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2 | ssl.CERT_NONE) if _mqtt.get("ssl", False) else False

    def load_loxone(self):
        try:
            if LOXONE_IP:
                self.loxone = {KEY_IP_ADDRESS: LOXONE_IP}
                self.loxone.update({KEY_UDP_PORT: UDP_PORT})
                save_json_file(LOXONE_CONFIG_FILE_PATH, self.loxone)
            else:
                self.loxone = load_json_file(LOXONE_CONFIG_FILE_PATH)
        except:
            self.loxone = {KEY_IP_ADDRESS: LOXONE_DEFAULT_IP, KEY_UDP_PORT: UDP_PORT}
            save_json_file(LOXONE_CONFIG_FILE_PATH, self.loxone)

    def load_definitions(self):
        global DOWNLOAD_URL_DEFINITIONS
        try:
            download_url_definitions = DOWNLOAD_URL_DEFINITIONS
            if not download_url_definitions.endswith("/"):
                download_url_definitions += "/"
            download_url_definitions += f"v{VERSION}/definitions.json"
            logger.info(f"Try to download definitions from {download_url_definitions}...")
            result = requests.get(f"{download_url_definitions}?cache_bypass={int(time.time())}",
                                  headers={"Cache-Control": "no-cache"}, timeout=5)
            logger.info("Successfully loaded definitions from GitHub.")
            self.definitions = json.loads(result.text)
            save_json_file(DEFINITIONS_CONFIG_FILE_PATH, self.definitions)
            logger.info("Definitions saved locally.")
        except Exception as e:
            logger.error(f"Failed to load definitions from GitHub: {str(e)}")
            logger.info("Trying to load definitions locally...")
            try:
                self.definitions = load_json_file(DEFINITIONS_CONFIG_FILE_PATH)
                logger.info("Successfully loaded definitions locally.")
            except Exception as e:
                self.definitions = {}
                logger.error("Failed to load definitions locally – no definitions available.")

    def handle_incoming_zigbee2mqtt_bridge_devices_message(self, device_list: list):
        mqtt_topic = "zigbee2mqtt"
        subscribe_topics = []
        for device in device_list:
            if device.get("type") != "Coordinator":
                device_name = device.get("friendly_name")
                model_name = device["definition"]["model"]
                if device_name and model_name:
                    topic = f"{mqtt_topic}/{device_name}"
                    self.devices[device_name] = {"model_name": model_name, "topic": topic}
                    subscribe_topics.append(topic)
        return subscribe_topics

    def handle_incoming_hue2mqtt_bridge_devices_message(self, device_list: list):
        mqtt_topic = "hue2mqtt"
        subscribe_topics = []
        for device_name in device_list:
            model_name = device_list[device_name]
            if device_name and model_name:
                topic = f"{mqtt_topic}/{device_name}"
                self.devices[device_name] = {"model_name": model_name, "topic": topic}
                subscribe_topics.append(f"{mqtt_topic}/{device_name}")
        return subscribe_topics

    def load(self):
        self.load_loxone()
        self.load_mqtt()
        self.load_definitions()


config = Config(update_interval_minutes=DEFINITIONS_UPDATE_INTERVAL_MIN)
config.load()
