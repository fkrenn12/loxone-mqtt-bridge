from contextlib import asynccontextmanager
from config import *
from constants import *
from utils import *
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import models
from logger import logger
from mqtt_node import fast_mqtt
from ws_node import ws_client
from udp2mqtt import udp2mqtt
from udp2ws import udp2ws
from udp_node import UDPServerProtocol
import os
import signal
import asyncio

description = """
## 🚀🚀 Loxone-MQTT Bridge 🚀🚀
### MQTT-Broker 
*
*
"""


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    try:
        await start_udp_server()
        await connect_websocket_client()
        await connect_mqtt_broker()
    except Exception as e:
        logger.error(e)
        logger.info("👎 Shutting down ...docker engine will restart the container.")
        await shutdown_services()
        os.kill(os.getpid(), signal.SIGTERM)
    yield
    await shutdown_services()


async def start_udp_server():
    try:
        await asyncio.get_event_loop().create_datagram_endpoint(
            lambda: UDPServerProtocol(udp2mqtt, udp2ws),
            local_addr=("0.0.0.0", config.loxone.get(KEY_UDP_PORT, UDP_PORT)),
        )
        logger.info("✅ UDP server started successfully.")
    except Exception as e:
        raise Exception(f"🤢 Error starting UDP server: {e}")


async def connect_websocket_client():
    try:
        if await ws_client.connect():
            logger.info(f"✅ Successfully connected to WebSocket: {ws_client.url}")
            asyncio.get_event_loop().create_task(ws_client.listen())
        else:
            logger.warning(f"⚠️ WebSocket connection attempt failed: {ws_client.url}")
    except Exception as e:
        raise Exception(f"🤢 Error connecting to WebSocket client {ws_client.url}:\n\r{e}")


async def connect_mqtt_broker():
    try:
        logger.info(
            f"🔌 MQTT Try first connection to broker: {fast_mqtt.config.username}@{fast_mqtt.config.host}:{fast_mqtt.config.port}")
        await asyncio.wait_for(fast_mqtt.mqtt_startup(), timeout=2)
        logger.info("✅ MQTT connected successfully.")
    except asyncio.TimeoutError:
        raise Exception(
            f"⏲️🤢 MQTT connecting timed out - check broker settings: '{fast_mqtt.config.username}'@{fast_mqtt.config.host}:{fast_mqtt.config.port}"
        )
    except Exception as e:
        raise Exception(f"🤢 Unexpected MQTT connection error: {e}")


async def shutdown_services():
    logger.info("🔌 Shutting down services gracefully...")
    await fast_mqtt.mqtt_shutdown()
    await ws_client.close()
    config.stop()
    logger.info("👍 Shutdown complete.")


app = FastAPI(lifespan=_lifespan,
              title="Loxone MQTT Bridge",
              version="1.0.0",
              summary="Handle and bridging Loxone UDP messages to MQTT.",
              debug=False,
              description=description)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Optional: Auf bestimmte Domains beschränken
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static-Files
app.mount("/frontend-html", StaticFiles(directory="frontend-html"), name="frontend-html")


@app.get("/api/definitions")
async def get_definitions():
    try:
        return load_json_file(DEFINITIONS_CONFIG_FILE_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading the configuration: {str(e)}")


@app.post("/api/definitions")
async def update_definitions(new_config: dict):
    try:
        save_json_file(DEFINITIONS_CONFIG_FILE_PATH, new_config)
        return {"success": True, "message": "Successfully updated the configuration!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving the configuration: {str(e)}")


@app.get("/api/loxone")
async def get_loxone_config():
    try:
        return load_json_file(LOXONE_CONFIG_FILE_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading the configuration: {str(e)}")


@app.post("/api/loxone")
async def update_loxone_config(new_config: dict):
    try:
        save_json_file(LOXONE_CONFIG_FILE_PATH, new_config)
        config.loxone = load_json_file(LOXONE_CONFIG_FILE_PATH)
        return {"success": True, "message": "Successfully updated the configuration!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving the configuration: {str(e)}")


@app.get("/api/mqtt")
async def get_mqtt():
    try:
        return load_json_file(MQTT_CONFIG_FILE_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading the configuration: {str(e)}")


@app.post("/api/mqtt")
async def update_mqtt(new_config: dict):
    try:
        save_json_file(MQTT_CONFIG_FILE_PATH, new_config)
        return {"success": True, "message": "Successfully updated the configuration!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving the configuration: {str(e)}")


@app.get("/api/mqtt-restart")
async def restart_mqtt():
    import asyncio
    _mqtt = load_json_file(MQTT_CONFIG_FILE_PATH)
    try:
        await fast_mqtt.client.disconnect()
        await asyncio.sleep(2)
        logger.debug(
            f'Try connecting to {_mqtt["host"]}, {_mqtt["port"]}, {_mqtt["username"]}, {bool(int(_mqtt["ssl"]))}...')
        fast_mqtt.client.set_auth_credentials(_mqtt["username"], _mqtt["password"])
        # ssl context accepts selfsigned certificates
        _ssl = bool(int(_mqtt["ssl"]))
        _ssl = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2 | ssl.CERT_NONE) if _ssl else False
        await asyncio.wait_for(fast_mqtt.client.connect(host=_mqtt["host"], port=_mqtt["port"], ssl=_ssl), 5)
        return models.Response(connected=True).model_dump(exclude={"reason"})
    except Exception as e:
        return models.Response(connected=False,
                               reason=str(f"Cannot connect to {_mqtt["host"]}:{_mqtt["port"]}")).model_dump()


@app.get("/api/mqtt-connection-state")
async def get_mqtt_connection_state():
    try:
        return {"connected": bool(fast_mqtt.client.is_connected)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving connection state: {str(e)}")


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    try:
        with open("frontend-html/index.html", "r", encoding="utf-8") as file:
            html_content = file.read()
        print(HOST_IP)
        if HOST_IP:
            html_content = html_content.replace("127.0.0.1", HOST_IP)
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>index.html not found</h1>", status_code=404)


@app.get("/api/restart")
async def restart_server():
    os.kill(os.getpid(), signal.SIGTERM)
    return {"message": "Server wird neu gestartet..."}


if __name__ == "__main__":
    import asyncio
    from uvicorn import Config, Server

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    config = Config("main:app", host="0.0.0.0", port=API_PORT, reload=False, log_level="error")
    server = Server(config)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.serve())
