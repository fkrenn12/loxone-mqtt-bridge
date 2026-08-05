import asyncio
import websockets
import json
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from logger import logger
from config import *
from matter import compare_states
from ws2udp import ws_event_callback

HA_URL = f"ws://{HOME_ASSISTANT_IP}:8123/api/websocket"


class WebSocketClient:
    def __init__(self, url, token, event_callback=None, reconnect_interval=5):
        self.url = url
        self.token = token
        self.websocket = None
        self.reconnect_interval = reconnect_interval
        self.running = True
        self.event_callback = event_callback
        self.lock = asyncio.Lock()

    async def connect(self):
        while self.running:
            try:
                logger.info(f"🔌 WS Try connection to Home Assistant WebSocket {self.url} ...")
                self.websocket = await websockets.connect(self.url)
                connect_response = await self.websocket.recv()
                if connect_response and json.loads(connect_response).get("type") == "auth_required":
                    await self.websocket.send(json.dumps({
                        "type": "auth",
                        "access_token": self.token
                    }))
                    auth_response = await self.websocket.recv()
                    auth_data = json.loads(auth_response)
                    if auth_data.get("type") == "auth_ok":
                        logger.info(f"❤️ WS Successfully authenticates: {auth_data}")
                        return True  # successfully connected
                    else:
                        raise Exception(f"❌ WS Authentication failed: {auth_data}")
                else:
                    return True  # successfully connected
            except Exception as e:
                logger.error(f"⚠️ WS Connection error: {e}. Next try to connect in {self.reconnect_interval} seconds.")
                await asyncio.sleep(self.reconnect_interval)  # Wartezeit vor neuer Verbindung

    async def send(self, message: dict):
        if self.websocket is None:
            raise ConnectionError("⚠️ WS WebSocket not connected. Need connect first.")
        try:
            async with self.lock:
                await self.websocket.send(json.dumps(message))
                logger.info(f"📤 WS message sent: {message}")
        except Exception as e:
            logger.error(f"⚠️ WS Error sending a message: {e}")
            raise

    async def receive(self):
        try:
            message = await self.websocket.recv()
            logger.info(f"📨 WS Message received: {message}")
            return json.loads(message)
        except Exception as e:
            logger.error(f"⚠️ WS Error reading a message: {e}")
            raise

    async def subscribe_to_events(self, event_type: str):
        await self.send({
            "id": 1,
            "type": "subscribe_events",
            "event_type": event_type
        })
        logger.info(f"📡 WS Subscribing Event-Typ: {event_type}")

    async def listen(self):
        while self.running:
            try:
                if self.websocket is None:
                    await self.connect()
                # Subscribe to events (necessary for every new connection)
                await self.subscribe_to_events("state_changed")
                logger.info(f"📡 WS Starte Event-Überwachung")
                # listen to events
                while self.running:
                    event = await self.receive()
                    try:
                        if self.event_callback:
                            await self.event_callback(event)
                    except Exception as e:
                        logger.error(f"WS Error in event handling: {e}")
            except (ConnectionClosedError, ConnectionClosedOK) as e:
                logger.warning(f"❌ Verbindung getrennt: {e}. Versuche erneut zu verbinden...")
                await asyncio.sleep(self.reconnect_interval)  # Wartezeit vor erneutem Verbindungsversuch
            except Exception as e:
                logger.error(f"⚠️ Fehler bei der Event-Überwachung: {e}")
                await asyncio.sleep(self.reconnect_interval)  # Wartezeit vor erneutem Versuch

    async def close(self):
        self.running = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            logger.info("🔌 Verbindung geschlossen.")


ws_client = WebSocketClient(url=HA_URL, token=HOME_ASSISTANT_TOKEN,
                            event_callback=ws_event_callback, reconnect_interval=5)
