import asyncio
import json
import socket
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
import aiodns
from fastapi import FastAPI, Body, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi_mqtt import FastMQTT, MQTTConfig
from gmqtt import Client as MQTTClient
from fastapi.middleware.cors import CORSMiddleware
import models
import ssl
from udp import UDPServerProtocol
import sys
import subprocess
import os
from constants import *
from logger import logger
from init_config import write_init_config_devices, write_init_config_mqtt, write_init_config_loxone
UDP_PORT = filename = os.environ.get('UDP_PORT', None)
UDP_PORT = int(UDP_PORT) if UDP_PORT else UDP_DEFAULT_PORT
API_PORT = filename = os.environ.get('API_PORT', None)
API_PORT = int(API_PORT) if API_PORT else API_DEFAULT_PORT


def is_running_in_container():
    return Path('/run/.dockerenv').is_file() or Path('/.dockerenv').is_file()


if is_running_in_container():
    logger.info("Running in docker container")
    CONFIG_PATH = Path("../config")
else:
    logger.info("Running on host")
    CONFIG_PATH = Path("../.loxone-mqtt-bridge/config")

MQTT_CONFIG_FILE_PATH = Path(f"{CONFIG_PATH}/mqtt.json")
MODELS_CONFIG_FILE_PATH = Path(f"{CONFIG_PATH}/models.json")
DEVICES_CONFIG_FILE_PATH = Path(f"{CONFIG_PATH}/devices.json")
LOXONE_CONFIG_FILE_PATH = Path(f"{CONFIG_PATH}/loxone.json")


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


try:
    config = load_json_file(MQTT_CONFIG_FILE_PATH)
except:
    write_init_config_mqtt(MQTT_CONFIG_FILE_PATH)
    config = load_json_file(MQTT_CONFIG_FILE_PATH)

try:
    devices = load_json_file(DEVICES_CONFIG_FILE_PATH)
except:
    write_init_config_devices(DEVICES_CONFIG_FILE_PATH)
    devices = load_json_file(DEVICES_CONFIG_FILE_PATH)

try:
    loxone = load_json_file(LOXONE_CONFIG_FILE_PATH)
except:
    write_init_config_loxone(LOXONE_CONFIG_FILE_PATH)
    loxone = load_json_file(LOXONE_CONFIG_FILE_PATH)

modeldefs = load_json_file(MODELS_CONFIG_FILE_PATH)

try:
    socket.gethostbyname('mosquitto')
    # we are on docker container with running service mosquitto
    # we want to connect to this first
    DEFAULT_BROKER = 'mosquitto'
except Exception as e:
    DEFAULT_BROKER = 'mqtt.mosquitto.org'

description = """
## 🚀🚀 Loxone-MQTT Bridge 🚀🚀
### MQTT-Broker Credentials 
* **Set credentials and connect** (_implemented_)\n
* **Get credentials information and connection state** (_implemented_)\n
"""

mqtt_config = MQTTConfig(
    host=config.get("HOST", DEFAULT_BROKER),
    port=int(config.get("PORT", f"{MQTT_DEFAULT_PORT}")),
    keepalive=60,
    username=config.get("USERNAME", str()),
    password=config.get("PASSWORD", str()),
    reconnect_delay=10,
    reconnect_retries=200000,
    ssl=bool(int(config.get("SSL", "0"))),
)

fast_mqtt = FastMQTT(config=mqtt_config)


def udp_send(data):
    logger.info(f"Sending UDP: {data}")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if type(data) is not bytes:
        data = data.encode(encoding="utf-8")
    s.sendto(data, (loxone.get("ip-address"), loxone.get("udp_port", UDP_PORT)))
    s.close()


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    try:
        loop = asyncio.get_event_loop()
        server_transport, server_protocol = await loop.create_datagram_endpoint(
            lambda: UDPServerProtocol(udp2mqtt),
            local_addr=("0.0.0.0", loxone.get("udp_port", UDP_PORT)),
        )
        try:
            await asyncio.wait_for(fast_mqtt.mqtt_startup(), 2)
        except asyncio.TimeoutError:
            raise Exception("MQTT startup timed out - check MQTT broker settings")
    except Exception as e:
        logger.error(f'Startup failed - {e}')
    yield
    await fast_mqtt.mqtt_shutdown()


app = FastAPI(lifespan=_lifespan,
              title="Loxone MQTT Bridge",
              version="1.0.0",
              contact={"name": "Franz Krenn",
                       "email": "office@fkrenn.at"},
              summary="Handling Loxone UDP messages and bridging with MQTT.",
              description=description)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Optional: Auf bestimmte Domains beschränken
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static-Files (optional, um den gesamten Ordner zu mounten)
app.mount("/frontend-html", StaticFiles(directory="frontend-html"), name="frontend-html")


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
        logger.error(f"Error during int or floating point conversion: {e}")
        return value


def apply_value_mapping(model: dict, key: str, value: Any):
    value = str(value).lower()
    mapping = model["value_mappings"].get(key)
    if not mapping and model.get("convert_bool2int"):
        mapping = {"true": 1, "false": 0}

    return mapping.get(value, value) if mapping else value


def get_message_formats(model: dict, key: str):
    default_format = model.get("default_message_format", [])
    specific_format = model.get("specific_message_formats", {}).get(key)

    if isinstance(default_format, dict):
        default_format = [default_format]

    return specific_format if specific_format else default_format


def udp2mqtt(msg: str):
    # logger.info(f"Received UDP: {msg}")
    splitted = msg.split("/")
    if len(splitted) == 2:
        device_name = splitted[0]
        key = None
        value = splitted[1]
    elif len(splitted) == 3:
        device_name = splitted[0]
        key = splitted[1]
        value = splitted[2]
    else:
        logger.error(f"Invalid message format:{msg}")
        return
    model_name = devices.get(device_name)
    if not model_name:
        logger.error(f"No information found for device: {device_name}")
        return
    model = next((m for m in modeldefs["models"] if m["name"] == model_name), None)
    if not model:
        logger.error(f"No information found modeling to UDP: {model_name}")
        return
    exposes = model.get("exposes", [])

    default_expose = model.get("default_expose")

    if key is None:
        key = default_expose

    if key not in exposes:
        logger.error(f"Key {key} not in value keys {exposes}")
        return

    value = apply_value_mapping(model, key, value)
    value = to_int_or_float_if_possible(value)
    # logger.info(f"Publishing MQTT: {device_name}/{key} {value}")
    payload = {key: value}
    topic = model.get("mqtt_topic", "")
    if topic:
        topic = f"{topic}/{device_name}/set"
        logger.info(f"Publishing MQTT: {topic} {payload}")
        fast_mqtt.publish(topic, json.dumps(payload), qos=1)


def mqtt2udp(topic: str, payload: dict):
    send = []
    device_name = topic.split("/")[-1]
    model_name = devices.get(device_name)

    if not model_name:
        logger.error(f"No information found for device: {device_name}")
        return []

    # print("Device Name: ", device_name, "Model Name:", model_name)
    model = next((m for m in modeldefs["models"] if m["name"] == model_name), None)

    if not model:
        logger.error(f"No information found modeling to UDP: {model_name}")
        return []

    exposes = model.get("exposes", [])
    # print("Value Keys: ", exposes)

    for key in exposes:
        value = payload.get(key)
        is_default_key = model.get("default_expose") == key
        # print(f"is_default_key: {is_default_key}, Key: {key}, Value: {value}")

        if value is not None:
            value = str(value).lower()
            value = apply_value_mapping(model, key, value)

            message_formats = get_message_formats(model, key)
            for message_format in message_formats:
                topic_str = device_name if is_default_key else f"{device_name}/{key}"
                send.append(message_format.format(topic=topic_str, value=value))

    return send


async def mqtt_incoming_message_handler(client, topic: str, payload: str, qos: int, properties: Any):
    try:
        payload = json.loads(payload)
        # udp handling
        tosend = mqtt2udp(topic, payload)
        for udp_packet in tosend:
            udp_send(json.dumps(udp_packet))
        # mqtt handling
        # topic, payload = mqtt_transformation(topic, payload)
        # fast_mqtt.publish(topic, payload, qos=qos, properties=properties)
    except Exception as e:
        logger.error(f'Error processing message {e}')


@fast_mqtt.on_connect()
def connect(client: MQTTClient, flags: int, rc: int, properties: Any):
    # client.subscribe(f"{ROOT_TOPIC}/#")  # subscribing mqtt topic
    username = client._username.decode() if type(client._username) is bytes else client._username
    password = client._password.decode() if type(client._password) is bytes else client._password
    host = client._host.decode() if type(client._host) is bytes else client._host
    logger.info(
        f"Connected to: {host}:{client._port} {username} flags {flags}, rc {rc}, properties {properties}")
    logger.debug(f"mqtt_config_file_path: {MQTT_CONFIG_FILE_PATH}")
    mqtt_credentials = load_json_file(MQTT_CONFIG_FILE_PATH)
    mqtt_credentials["LAST_CONNECTION_TIME"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time()))
    mqtt_credentials["HOST"] = host
    mqtt_credentials["PORT"] = client._port
    mqtt_credentials["USERNAME"] = username
    mqtt_credentials["PASSWORD"] = password
    mqtt_credentials["SSL"] = str(int(type(client._ssl) == ssl.SSLContext))
    save_json_file(MQTT_CONFIG_FILE_PATH, mqtt_credentials)
    devices_list = list(devices.keys())
    mqtt_mapping = {}
    # {"TS004_2":"zigbee2mqtt", "ZG-102ZA":"zigbee2mqtt", ... usw}
    for model in modeldefs.get("models", []):
        model_name = model.get("name")
        mqtt_topic = model.get("mqtt_topic")
        if model_name and mqtt_topic:
            mqtt_mapping[model_name] = mqtt_topic
    subscribe_topics = []
    for device in devices_list:
        model = devices.get(device)
        mqtt_topic = mqtt_mapping.get(model, "")
        # print(f"Device: {device}, Model: {model}, MQTT Topic: {mqtt_topic}")
        if mqtt_topic and model:
            subscribe_topics.append(f"{mqtt_topic}/{device}")
    logger.debug(f"Subscribing to topics: {subscribe_topics}")
    for topic in subscribe_topics:
        client.subscribe(topic, qos=1)


@fast_mqtt.on_message()
async def message(client: MQTTClient, topic: str, payload: bytes, qos: int, properties: Any):
    logger.info(f"Received MQTT: {topic}, {payload.decode()}")
    await mqtt_incoming_message_handler(client, topic, payload.decode(), qos, properties)


@fast_mqtt.on_disconnect()
def disconnect(client: MQTTClient, packet, exc=None):
    logger.info("MQTT broker disconnected")


@fast_mqtt.on_subscribe()
def subscribe(client: MQTTClient, mid: int, qos: int, properties: Any):
    #  print("subscribed", client, mid, qos, properties)
    pass


@app.post("/mqtt-broker-connect",
          response_description='Result is true if successfully connected.\nReason gives an indication of failure.',
          description='Use credential settings of mqtt broker to connect',
          tags=['Broker'])
async def mqtt_broker_set_credentials_and_connect(credentials: models.BrokerCredentials =
                                                  Body(default=models.default_brokercredentials)) -> Any:
    _config = load_json_file(MQTT_CONFIG_FILE_PATH)
    host = credentials.host if credentials.host else _config.get("HOST", str())
    port = credentials.port if credentials.port else _config.get("PORT", MQTT_DEFAULT_PORT)
    username = credentials.username if credentials.username is not None else _config.get("USERNAME", str())
    password = credentials.password if credentials.password is not None else _config.get("PASSWORD", str())
    _ssl = credentials.ssl if credentials.ssl is not None else _config.get("SSL", 0)
    try:
        resolver = aiodns.DNSResolver(loop=asyncio.get_event_loop())
        await resolver.getaddrinfo(host, socket.AF_INET)
        try:
            await fast_mqtt.client.disconnect()
            await asyncio.sleep(1)
        except Exception as e:
            logger.debug(f'mqtt_broker_set_credentials_and_connect {e}')
        logger.debug('broker credentials and connecting {host}, {port}, {username}, {password}, {bool(_ssl)}')
        fast_mqtt.client.set_auth_credentials(username, password)
        # ssl context accepts selfsigned certificates
        _ssl = False if _ssl == 0 else ssl.SSLContext(ssl.PROTOCOL_TLSv1_2 | ssl.CERT_NONE)
        await asyncio.wait_for(fast_mqtt.client.connect(host=host, port=port, ssl=_ssl), 5)
        return models.Response(connected=True).model_dump(exclude={"reason"})
    except Exception as e:
        return models.Response(connected=False, reason=str(e)).model_dump()


@app.get("/mqtt-broker-information",
         response_description='Credentials and status of connection',
         description='Information about actual broker connection state',
         tags=['Broker'])
async def mqtt_broker_information() -> Any:
    _config = load_json_file(MQTT_CONFIG_FILE_PATH)
    try:
        if fast_mqtt.client.is_connected:
            return models.ResponseBrokerCredentials(connected=True,
                                                    host=_config.get("HOST"),
                                                    port=_config.get("PORT"),
                                                    username=_config.get("USERNAME"),
                                                    password=_config.get("PASSWORD"),
                                                    ssl=_config.get("SSL"),
                                                    last_connection_time=_config.get(
                                                        "LAST_CONNECTION_TIME")).model_dump(exclude={"password"})

        else:
            return models.ResponseBrokerCredentials(connected=False).model_dump(include={"connected"})

    except Exception as e:
        return models.Response(connected=False, reason=str(e)).model_dump()


@app.get("/api/models")
async def get_models():
    try:
        return load_json_file(MODELS_CONFIG_FILE_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading the configuration: {str(e)}")


@app.post("/api/models")
async def update_models(new_config: dict):
    try:
        save_json_file(MODELS_CONFIG_FILE_PATH, new_config)
        return {"success": True, "message": "Successfully updated the configuration!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving the configuration: {str(e)}")


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    try:
        with open("frontend-html/index.html", "r", encoding="utf-8") as file:
            html_content = file.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>index.html not found</h1>", status_code=404)


@app.get("/api/restart")
async def restart_server():
    logger.info("Restarting Uvicorn server...")
    python = sys.executable
    uvicorn_command = ["uvicorn", "main:app", "--reload", "--workers", "1", "--host", "0.0.0.0", "--port",
                       f"{API_PORT}"]
    subprocess.Popen([python, "-m"] + uvicorn_command)
    sys.exit(0)
