from channels.generic.websocket import AsyncWebsocketConsumer
import json
from tracker.tasks import celery_test


class CeleryConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add('celery', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('celery', self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        data = text_data or bytes_data.decode('utf-8')
        if data.lower() == 'ping':
            celery_test.apply_async(countdown=1)
        else:
            await self.close(400)

    async def pong(self, event):
        await self.send(text_data=json.dumps(event))
