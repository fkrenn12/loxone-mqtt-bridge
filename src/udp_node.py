import asyncio
from logger import logger
from constants import *
import socket
from config import config, UDP_PORT
from threading import Lock

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
    def __init__(self, receive_callback_mqtt=None, receive_callback_ws=None):
        self.transport = None
        self.receive_callback_mqtt = receive_callback_mqtt
        self.receive_callback_ws = receive_callback_ws

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
            # so we use it to decide between zigbee and matter
            if "." in entity_id:
                if self.receive_callback_ws:
                    self.receive_callback_ws(message)
            else:
                if self.receive_callback_mqtt:
                    self.receive_callback_mqtt(message)
        else:
            return

    def connection_lost(self, exc):
        logger.error("UDP server connection closed")

import asyncio
import socket
import argparse


async def udp_broadcast_loop(ip, port, message, interval):
    """
    Sendet eine UDP-Broadcast-Nachricht in einem asynchronen Intervall.

    Args:
        ip (str): Die Ziel-Broadcast-Adresse (z. B. 192.168.0.255 oder <broadcast>).
        port (int): Der Ziel-UDP-Port.
        message (str): Die Nachricht, die gesendet werden soll.
        interval (int): Das Intervall in Sekunden zwischen den Nachrichten.
    """
    print(f"Starte asynchronen UDP-Broadcaster...\nSende Broadcast an {ip}:{port}")
    print(f"Nachricht: {message}")
    print(f"Wiederholungsintervall: {interval} Sekunden\n")

    # Erstelle UDP-Socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setblocking(False)

    loop = asyncio.get_event_loop()

    while True:
        try:
            await loop.sock_sendto(sock, message.encode(), (ip, port))
            print(f"Broadcast gesendet: {message}")
        except Exception as e:
            print(f"Fehler beim Senden des Broadcasts: {e}")
        await asyncio.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Asynchrones UDP Broadcaster-Skript")
    parser.add_argument("--ip", type=str, default="192.168.0.255", help="Broadcast-Adresse (Standard: 192.168.0.255)")
    parser.add_argument("--port", type=int, default=12345, help="UDP-Port (Standard: 12345)")
    parser.add_argument("--message", type=str, default="Async Hello, World!",
                        help="Nachricht, die gesendet wird (Standard: Async Hello, World!)")
    parser.add_argument("--interval", type=int, default=5,
                        help="Zeitintervall in Sekunden zwischen den Nachrichten (Standard: 5 Sekunden)")

    args = parser.parse_args()

    try:
        asyncio.run(udp_broadcast_loop(args.ip, args.port, args.message, args.interval))
    except KeyboardInterrupt:
        print("\nBroadcast gestoppt. Programm beendet.")
