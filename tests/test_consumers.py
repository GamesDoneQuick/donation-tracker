import datetime
import json
from decimal import Decimal

import dateutil
import pytz
from asgiref.sync import async_to_sync, sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, SimpleTestCase
from tracker import models, eventutil
from tracker.consumers import PingConsumer, DonationConsumer

from .util import today_noon


class TestPingConsumer(SimpleTestCase):
    @async_to_sync
    async def test_ping_consumer(self):
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


class TestDonationConsumer(TransactionTestCase):
    # since the async part means THREADS, means that this transaction has to be treated differently
    def setUp(self):
        self.donor = models.Donor.objects.create()
        self.event = models.Event.objects.create(
            receivername='Médecins Sans Frontières',
            targetamount=1,
            paypalemail='msf@example.com',
            paypalcurrency='USD',
            datetime=today_noon,
        )
        self.donation = models.Donation.objects.create(
            timereceived=today_noon,
            comment='',
            amount=Decimal(1.5),
            domain='LOCAL',
            donor=self.donor,
            event=self.event,
            transactionstate='COMPLETED',
        )

    def tearDown(self):
        self.donation.delete()
        self.donor.delete()
        self.event.delete()

    @async_to_sync
    async def test_donation_consumer(self):
        communicator = WebsocketCommunicator(DonationConsumer, '/tracker/ws/donation/')
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected, 'Could not connect')
        await sync_to_async(eventutil.post_donation_to_postbacks)(self.donation)
        result = json.loads(await communicator.receive_from())
        expected = {
            'type': 'donation',
            'id': self.donation.id,
            'timereceived': str(self.donation.timereceived),
            'comment': self.donation.comment,
            'amount': self.donation.amount,
            'donor__visibility': self.donor.visibility,
            'donor__visiblename': self.donor.visible_name(),
            'new_total': self.donation.amount,
            'domain': self.donation.domain,
        }
        self.assertEqual(result, expected)
