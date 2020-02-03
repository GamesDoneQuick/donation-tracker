import asyncio
import datetime

import dateutil
import pytz
from channels.testing import WebsocketCommunicator
from django.test import SimpleTestCase

from tracker.consumers import PingConsumer


class TestPingConsumer(SimpleTestCase):
    def test_ping_consumer(self):
        async def internal():
            communicator = WebsocketCommunicator(PingConsumer, '/tracker/ws/ping/')
            connected, subprotocol = await communicator.connect()
            self.assertTrue(connected, 'Could not connect')
            await communicator.send_to(text_data='PING')
            result = await communicator.receive_from()
            # TODO: python 3.7 has datetime.datetime.fromisoformat
            date = dateutil.parser.parse(result)
            now = datetime.datetime.now(pytz.utc)
            self.assertTrue(
                (date - now).total_seconds() < 5,
                msg=f'{date} and {now} differed by more than five seconds',
            )
            await communicator.disconnect()

        loop = asyncio.get_event_loop()
        loop.run_until_complete(internal())
        loop.close()
