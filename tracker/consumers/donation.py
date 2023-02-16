import json

from channels.generic.websocket import AsyncWebsocketConsumer


class DonationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add('donations', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('donations', self.channel_name)

    async def donation(self, event):
        await self.send(text_data=json.dumps(event))
