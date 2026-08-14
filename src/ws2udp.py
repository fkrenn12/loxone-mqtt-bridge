from matter import compare_states
from logger import logger
import asyncio
from udp_node import udp_send

lock = asyncio.Lock()


async def ws_event_callback(event):
    if event and "event" in event:
        try:
            event_data = event["event"]["data"]
            entity_id = event_data["new_state"]["entity_id"]
            # print(f"entity_id: {entity_id}")
            # print("old", event_data["old_state"])
            # print("new", event_data["new_state"])
        except Exception as e:
            logger.error(f"Error WS event data not processable: {e}")
            return

        changed_states = compare_states(event_data["old_state"], event_data["new_state"])
        logger.info(f"📨 WS Event state changed: {entity_id} - {changed_states}")
        send = []
        for key, value in changed_states.items():
            # convert true/false and on/off into 1 and 0
            if isinstance(value, bool):
                value = int(value)
            elif isinstance(value, str) and value.lower() in ["on", "off"]:
                value = 1 if value.lower() == "on" else 0
            send.append(f"{entity_id}/{key}/{value}")

        for s in send:
            udp_send(s)
        # print("send 2 UDP", send)
        # send to udp
        # if event_data.get("entity_id") == entity_id:
        #    new_state = event_data["new_state"]["state"]
        #    print(new_state)
        # logger.info(f"⚡ Zustand von {entity_id} geändert: {new_state}")
        # if new_state == "on":
        #    logger.info(f"💡 {entity_id} wurde eingeschaltet!")
        # elif new_state == "off":
        #    logger.info(f"💤 {entity_id} wurde ausgeschaltet!")
