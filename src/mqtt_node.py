import asyncio
from logger import logger
from config import config
from fastapi_mqtt import FastMQTT
from gmqtt import Client as MQTTClient
import json
from mqtt2udp import mqtt2udp
from udp_node import udp_send
from typing import Any


logger.info(f"MQTT-Broker settings: host={config.mqtt.host} port={config.mqtt.port} username={config.mqtt.username},"
            f" password={config.mqtt.password}, ssl={config.mqtt.ssl}")

fast_mqtt = FastMQTT(config=config.mqtt, mqtt_logger=logger)


async def restart_mqtt_broker():
    await fast_mqtt.mqtt_shutdown()
    logger.info("MQTT broker stopped. Starting again...")
    await asyncio.wait_for(fast_mqtt.mqtt_startup(), 10)
    logger.info("MQTT broker started.")


def mqtt_is_connected():
    return fast_mqtt.client.is_connected


@fast_mqtt.on_subscribe()
def subscribe(client: MQTTClient, mid: int, qos: int, properties: Any):
    pass


@fast_mqtt.on_message()
async def message(client: MQTTClient, topic: str, payload: bytes, qos: int, properties: Any):
    logger.info(f"Received MQTT: {topic}, {payload.decode()[:100]}{'...' if len(payload) > 100 else ''}")
    try:
        payload = json.loads(payload)
        if topic == "zigbee2mqtt/bridge/devices":
            # subscribe_topics = await handle_incoming_zigbee2mqtt_bridge_devices_message(payload)
            subscribe_topics = config.handle_incoming_zigbee2mqtt_bridge_devices_message(payload)
            logger.debug(f"Subscribing to topics: {subscribe_topics}")
            for topic in subscribe_topics:
                client.subscribe(topic, qos=1)
            return
        elif topic == "hue2mqtt/bridge/devices":
            # subscribe_topics = await handle_incoming_hue2mqtt_bridge_devices_message(payload)
            subscribe_topics = config.handle_incoming_hue2mqtt_bridge_devices_message(payload)
            logger.debug(f"Subscribing to topics: {subscribe_topics}")
            for topic in subscribe_topics:
                client.subscribe(topic, qos=1)
            return
        else:
            # all other topics
            # udp handling
            tosend = mqtt2udp(topic, payload)
            for udp_packet in tosend:
                udp_send(udp_packet)
        # mqtt handling
        # topic, payload = mqtt_transformation(topic, payload)
        # fast_mqtt.publish(topic, payload, qos=qos, properties=properties)
    except Exception as e:
        logger.error(f'Error processing message {e}')


@fast_mqtt.on_connect()
def connect(client: MQTTClient, flags: int, rc: int, properties: Any):
    # client.subscribe(f"{ROOT_TOPIC}/#")  # subscribing mqtt topic
    username = client._username.decode() if type(client._username) is bytes else client._username
    # password = client._password.decode() if type(client._password) is bytes else client._password
    host = client._host.decode() if type(client._host) is bytes else client._host
    # logger.info(
    #    f"Connected to: {host}:{client._port} {username} flags {flags}, rc {rc}, properties {properties}")
    client.subscribe("zigbee2mqtt/bridge/devices", qos=1)
    client.subscribe("hue2mqtt/bridge/devices", qos=1)


@fast_mqtt.on_disconnect()
def disconnect(client: MQTTClient, packet, exc=None):
    logger.info("MQTT broker disconnected")
