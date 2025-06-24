# consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class DeviceStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("device_status", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("device_status", self.channel_name)

    async def receive(self, text_data):
        # Optionally handle messages from client
        pass

    async def device_status(self, event):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[Consumer] device_status called with event: {event}")  # DEBUG
        await self.send(text_data=json.dumps({
            "type": "device.status",
            "data": event["data"]
        }))


