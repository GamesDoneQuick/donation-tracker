from channels.generic.websocket import AsyncWebsocketConsumer
import json


class CeleryConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add('celery', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('celery', self.channel_name)

    async def completion(self, event):
        await self.send(text_data=json.dumps(event))
