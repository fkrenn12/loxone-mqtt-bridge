import asyncio
from logger import logger
from constants import *
import socket
from config import config, UDP_PORT


def udp_send(data):
    dest_ip = config.loxone.get(KEY_IP_ADDRESS)
    dest_port = config.loxone.get(KEY_UDP_PORT, UDP_PORT)
    logger.info(f"Sending UDP: {data} to {dest_ip}:{dest_port}")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if type(data) is not bytes:
        data = data.encode(encoding="utf-8")
    s.sendto(data, (config.loxone.get(KEY_IP_ADDRESS), config.loxone.get(KEY_UDP_PORT, UDP_PORT)))
    s.close()


class UDPServerProtocol(asyncio.DatagramProtocol):
    def __init__(self, receive_callback=None):
        self.transport = None
        self.receive_callback = receive_callback

    def connection_made(self, transport):
        self.transport = transport
        logger.info("UDP server is up and running...")

    def datagram_received(self, data, addr):
        message = data.decode('utf-8')
        logger.info(f"Received UDP: {message} from {addr}")
        if self.receive_callback:
            self.receive_callback(message)

    def connection_lost(self, exc):
        logger.error("UDP server connection closed")
