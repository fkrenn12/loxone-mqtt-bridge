import asyncio
from utils import *
from logger import logger
from ws_node import ws_client
from matter import handle_matter_service

id_counter = 10


def udp2ws(msg: str):
    global id_counter
    # print(f"Received UDP: {msg}")
    # message formats
    splitted = msg.split("/")
    if len(splitted) == 2:
        # message format
        # domain.entity_id/service
        entity_id = splitted[0]
        domain = entity_id.split(".")[0]
        service = splitted[1]
        value = None
    elif len(splitted) == 3:
        # message format
        # domain.entity_id/service/value
        entity_id = splitted[0]
        domain = entity_id.split(".")[0]
        service = splitted[1]
        value = splitted[2]
    else:
        logger.error(f"Invalid message format:{msg}")
        return
    value = cast_to_numeric(value)
    try:
        value = json.loads(value)
    except:
        pass

    service, service_data = handle_matter_service(domain, service, value)
    id_counter += 1

    to_send = {
        "id": id_counter,  # Neue ID für diesen Aufruf
        "type": "call_service",
        "domain": f"{domain}",
        "service": f"{service}",
        "target": {"entity_id": f"{entity_id}"},
        "service_data": service_data
    }
    asyncio.create_task(ws_client.send(to_send))
