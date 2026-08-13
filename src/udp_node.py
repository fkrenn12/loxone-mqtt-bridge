import asyncio
from logger import logger
from constants import *
import socket
from config import config, UDP_PORT
from threading import Lock
import time
from datetime import datetime
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
        if len(split) > 1:
            entity_id = split[0]
            # . is splitting entity_id into domain and name
            # used to recognize zigbee and matter devices
            if "." in entity_id:
                if self.receive_callback_matter:
                    self.receive_callback_matter(message)
            else:
                if self.receive_callback_zigbee:
                    self.receive_callback_zigbee(message)
        else:
            return

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

