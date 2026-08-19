import asyncio
from logger import logger
from constants import *
import socket
from config import config, UDP_PORT
from threading import Lock
import time
from matter import handle_matter_service
from zigbee import handle_zigbee_service
from value_normalizers import validate_and_normalize
lock = Lock()


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
        if device == "ping" or service == "ping":
            return
        value = split[2] if len(split) > 2 else None
        is_matter = "." in device
        domain = device.split(".")[0] if is_matter else None
        entity_id = device if is_matter else None
        service, value = validate_and_normalize(domain, service, value, is_matter)
        if service is not None and is_matter and self.receive_callback_matter:
            service, service_data = handle_matter_service(domain, service, value)
            self.receive_callback_matter(domain, entity_id, service, service_data)
        elif service is not None and not is_matter and self.receive_callback_zigbee:
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
