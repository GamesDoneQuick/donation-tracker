import datetime

from channels.generic.websocket import AsyncWebsocketConsumer


class PingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def receive(self, text_data=None, bytes_data=None):
        data = text_data or bytes_data.decode('utf-8')
        if data == 'PING':
            await self.send(datetime.datetime.now(tz=datetime.timezone.utc).isoformat())
        else:
            await self.close(400)
