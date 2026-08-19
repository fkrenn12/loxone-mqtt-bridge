import asyncio
import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from config import *
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
        try:
            logger.info(f"🔌 WS Try first connection to {self.url}")
            self.websocket = await websockets.connect(self.url, open_timeout=10)  # do not use too short timeouts
            connect_response = await self.websocket.recv()
            if connect_response and json.loads(connect_response).get("type") == "auth_required":
                await self.websocket.send(json.dumps({
                    "type": "auth",
                    "access_token": self.token
                }))
                auth_data = json.loads(await self.websocket.recv())
                if auth_data.get("type") == "auth_ok":
                    logger.info(f"✅❤ ️ WS Successfully connected and authenticated")
                    return True  # successfully connected
                else:
                    raise Exception(f"❌ WS Authentication failed: {auth_data}")
            else:
                logger.info(f"✅  ️WS Successfully connected")
                return True  # successfully connected
        except Exception as e:
            self.websocket = None
            raise e

    async def reconnect_loop(self):
        while self.running:
            try:
                return await self.connect()
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
            await self.reconnect_loop()

    async def receive(self):
        try:
            message = await self.websocket.recv()
            logger.info(f"📨 WS Message received: {message}")
            return json.loads(message)
        except Exception as e:
            if self.running:
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
                    await self.reconnect_loop()
                # Subscribe to events (necessary for every new connection)
                await self.subscribe_to_events("state_changed")
                logger.info(f"📡 WS Subscribe to events")
                # listen to events
                while self.running:
                    event = await self.receive()
                    try:
                        if self.event_callback:
                            await self.event_callback(event)
                    except Exception as e:
                        logger.error(f"WS Error in event handling: {e} {event}")
            except (ConnectionClosedError, ConnectionClosedOK) as e:
                if self.running:
                    logger.warning(f"❌ Connection closed: {e}. Reconnecting...")
                await asyncio.sleep(self.reconnect_interval)
            except Exception as e:
                if self.running:
                    logger.error(f"⚠️ Error during waiting for event: {e}")
                await asyncio.sleep(self.reconnect_interval)

    async def close(self):
        self.running = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            logger.info("🔌 WS Connection closed.")


ws_client = WebSocketClient(url=HA_URL, token=HOME_ASSISTANT_TOKEN,
                            event_callback=ws_event_callback, reconnect_interval=5)
