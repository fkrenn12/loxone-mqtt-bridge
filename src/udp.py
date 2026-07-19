import asyncio
from logger import logger


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
