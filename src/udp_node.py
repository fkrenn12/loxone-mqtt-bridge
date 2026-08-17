import asyncio
from logger import logger
from constants import *
import socket
from config import config, UDP_PORT
from threading import Lock
import time

from matter import handle_matter_service
from zigbee import handle_zigbee_service
from utils import *
from datetime import datetime
from pydantic.color import COLORS_BY_NAME

lock = Lock()

SERVICES = ["color", "brightness", "color_temp", "turn_on", "turn_off", "state"]


def limit_to_percent(value):
    return min(max(value, 0), 100)


def validate_and_normalize(domain: str, service: str, value: str, is_matter: bool) -> tuple:
    """
    Validates the service and normalizes the value based on the service type.

    :param domain: The device domain (e.g., "zigbee" or "matter").
    :param service: The requested service (e.g., "brightness", "color").
    :param value: The input value.
    :param is_matter: Boolean indicating if the device is Matter.
    :return: A tuple (service, normalized_value) or (None, None) if validation fails.
    """
    if service not in SERVICES:
        logger.warning(f"Unknown service: {service}")
        return None, None

    # Attempt to parse the value
    parsed_value = _parse_value(value)
    if parsed_value is None:
        return None, None

    # Normalize the value based on the service type
    return service, _normalize_value(service, parsed_value)


def _parse_value(value: str) -> any:
    """Attempts to parse the value and cast to numeric if applicable."""
    try:
        value = json.loads(value)
    except (ValueError, TypeError):
        pass  # Ignore if value is not JSON

    try:
        return cast_to_numeric(value)  # Attempt to cast to numeric
    except Exception as e:
        logger.error(f"Failed parsing value: {value}. Error: {e}")
        return None


def _normalize_value(service: str, value: any) -> any:
    """Normalizes the value based on the specified service."""
    service_handlers = {
        "brightness": lambda val: limit_to_percent(val) if isinstance(val, int) else None,
        "state": lambda val: int(bool(val)),
        "color_temp": lambda val: val if isinstance(val, int) else None,
        "color": lambda val: _normalize_color(val),
    }
    handler = service_handlers.get(service)
    if not handler:
        logger.warning(f"Unsupported service: {service}")
        return None
    value = handler(value)

    # we do not handle black rgb value, because in this case color_temp  will define the light
    if service == "color" and value == [0, 0, 0]:
        return None

    return value


def _normalize_color(value: any) -> list | None:
    """Normalizes color information (HEX, RGB, or color names)."""
    if isinstance(value, int):
        # Convert Loxone color code to RGB
        try:
            return list(extract_rgb_components(value))
        except Exception as e:
            logger.error(f"Failed to extract RGB from color code '{value}': {e}")
            return None

    if isinstance(value, str):
        # Check for color names in known dictionaries
        try:
            # Retrieve color from known dictionaries or normalize as a list
            rgb = COLORS_BY_NAME.get(value) or COLORS_BY_NAME_DE.get(value)
            if rgb:
                return normalize_to_list(rgb)
        except Exception as e:
            logger.error(f"Error processing string color '{value}': {e}")
            return None

    # If the input is a list or tuple
    try:
        return normalize_to_list(value)
    except Exception as e:
        logger.error(f"Error normalizing color value: {value}. Error: {e}")
        return None


def validate_and_normalize_old(domain, service, value, is_matter):
    # validate service
    if service not in SERVICES:
        return None, None
    # validate value
    try:
        value = json.loads(value)
    except:
        pass
    value = cast_to_numeric(value)  # converts to numeric if possible
    if value is not None:
        if service == "brightness":
            value = limit_to_percent(value) if isinstance(value, int) else None
        elif service == "state":
            value = int(bool(value))
        elif service == "color_temp":
            value = value if isinstance(value, int) else None
        elif service == "color":
            if isinstance(value, int):
                # loxone color code
                try:
                    red, green, blue = extract_rgb_components(value)
                    value = [red, green, blue]
                except:
                    value = None
            else:
                # is string color as text or list or tuple
                try:
                    if value in COLORS_BY_NAME:
                        value = COLORS_BY_NAME[value]
                    elif value in COLORS_BY_NAME_DE:
                        value = COLORS_BY_NAME_DE[value]
                    value = normalize_to_list(value)
                except:
                    # color as list or tuple
                    try:
                        value = normalize_to_list(value)
                    except:
                        value = None

    return service, value


def udp_send(data):
    dest_ip = config.loxone.get(KEY_IP_ADDRESS)
    dest_port = config.loxone.get(KEY_UDP_PORT, UDP_PORT)
    logger.info(f"Sending UDP: {data} to {dest_ip}:{dest_port}")
    with lock:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if type(data) is not bytes:
            data = data.encode(encoding="utf-8")
        s.sendto(data, (config.loxone.get(KEY_IP_ADDRESS), config.loxone.get(KEY_UDP_PORT, UDP_PORT)))
        s.close()


class UDPServerProtocol(asyncio.DatagramProtocol):
    def __init__(self, receive_callback_zigbee=None, receive_callback_matter=None):
        self.transport = None
        self.receive_callback_zigbee = receive_callback_zigbee
        self.receive_callback_matter = receive_callback_matter

    def connection_made(self, transport):
        self.transport = transport
        logger.info("UDP server is up and running...")

    def datagram_received(self, data, addr):
        message = data.decode('utf-8')
        logger.info(f"Received UDP: {message} from {addr}")
        split = message.split("/")
        if len(split) <= 1:
            return
        device = split[0]
        service = split[1]
        if service == "ping":
            return
        value = split[2] if len(split) > 2 else None
        is_matter = "." in device
        domain = device.split(".")[0] if is_matter else None
        entity_id = device if is_matter else None
        service, value = validate_and_normalize(domain, service, value, is_matter)
        if service and value is not None and is_matter and self.receive_callback_matter:
            service, service_data = handle_matter_service(domain, service, value)
            self.receive_callback_matter(domain, entity_id, service, service_data)
        elif service and value is not None and not is_matter and self.receive_callback_zigbee:
            service, service_data = handle_zigbee_service(device, service, value)
            self.receive_callback_zigbee(device, service, service_data)

    def connection_lost(self, exc):
        logger.error("UDP server connection closed")


async def udp_broadcast_loop(ip, port, message, interval):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    while True:
        try:
            to_send = f"{message}:UTC:{time.time()}"
            sock.sendto(to_send.encode(), (ip, port))
            logger.info(f"UDP Broadcast done: {to_send}")
        except Exception as e:
            logger.error(f"Error UDP broadcasting: {e}")
        await asyncio.sleep(interval)
