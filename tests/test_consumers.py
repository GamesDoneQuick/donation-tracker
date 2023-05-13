import datetime
import json
from decimal import Decimal
from unittest import mock

from asgiref.sync import async_to_sync, sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import Permission, User
from django.test import SimpleTestCase, TransactionTestCase

from tracker import eventutil, models
from tracker.api.serializers import DonationSerializer
from tracker.api.views.donations import DonationProcessingActionTypes
from tracker.consumers import DonationConsumer, PingConsumer
from tracker.consumers.processing import ProcessingConsumer, broadcast_processing_action
from tracker.util import utcnow

from .util import today_noon


class TestPingConsumer(SimpleTestCase):
    @async_to_sync
    async def test_ping_consumer(self):
        communicator = WebsocketCommunicator(
            PingConsumer.as_asgi(), '/tracker/ws/ping/'
        )
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected, 'Could not connect')
        await communicator.send_to(text_data='PING')
        result = await communicator.receive_from()
        date = datetime.datetime.fromisoformat(result)
        now = utcnow()
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
        self.challenge = models.Bid.objects.create(
            event=self.event, istarget=True, goal=500
        )
        self.choice = models.Bid.objects.create(event=self.event)
        self.option = models.Bid.objects.create(parent=self.choice, istarget=True)
        self.challenge_bid = models.DonationBid.objects.create(
            donation=self.donation, bid=self.challenge, amount=1
        )
        self.option_bid = models.DonationBid.objects.create(
            donation=self.donation, bid=self.option, amount=0.5
        )

    def tearDown(self):
        self.option_bid.delete()
        self.challenge_bid.delete()
        self.option.delete()
        self.choice.delete()
        self.challenge.delete()
        self.donation.delete()
        self.donor.delete()
        self.event.delete()

    @async_to_sync
    async def test_donation_consumer(self):
        communicator = WebsocketCommunicator(
            DonationConsumer.as_asgi(), '/tracker/ws/donation/'
        )
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected, 'Could not connect')
        await sync_to_async(eventutil.post_donation_to_postbacks)(self.donation)
        result = json.loads(await communicator.receive_from())
        expected = {
            'type': 'donation',
            'id': self.donation.id,
            'event': self.event.id,
            'timereceived': str(self.donation.timereceived),
            'comment': self.donation.comment,
            'amount': self.donation.amount,
            'donor__visibility': self.donor.visibility,
            'donor__visiblename': self.donor.visible_name(),
            'new_total': self.donation.amount,
            'domain': self.donation.domain,
            'bids': [
                {
                    'id': self.challenge.id,
                    'pk': self.challenge.id,
                    'total': self.challenge_bid.amount,
                    'parent': None,
                    'name': self.challenge.name,
                    'goal': self.challenge.goal,
                    'state': self.challenge.state,
                    'speedrun': self.challenge.speedrun_id,
                },
                {
                    'id': self.option.id,
                    'pk': self.option.id,
                    'total': self.option_bid.amount,
                    'parent': self.option.parent_id,
                    'name': self.option.name,
                    'goal': self.option.goal,
                    'state': self.option.state,
                    'speedrun': self.option.speedrun_id,
                },
            ],
        }
        self.assertEqual(result, expected)


class TestProcessingConsumer(TransactionTestCase):
    # since the async part means THREADS, means that this transaction has to be treated differently
    def setUp(self):
        self.user = User.objects.create(username='test')
        self.anonymous_user = User.objects.create(username='no permissions')
        self.user.user_permissions.add(
            Permission.objects.get(name='Can change donor'),
            Permission.objects.get(name='Can change donation'),
            Permission.objects.get(name='Can view all comments'),
        )
        # Force django to load the user permissions before the test, otherwise
        # async vs sync conflicts come up during the test
        self.user.has_perm('tracker.change_donation')
        self.anonymous_user.has_perm('tracker.change_donation')

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
        self.serialized_donation = DonationSerializer(
            self.donation, with_permissions=('tracker.change_donation',)
        ).data

    def tearDown(self):
        self.donation.delete()
        self.donor.delete()
        self.event.delete()

    def get_communicator(self, *, as_user):
        communicator = WebsocketCommunicator(
            ProcessingConsumer.as_asgi(), '/tracker/ws/processing/'
        )
        # This is awkward, but Channels 2.x does not let you set the scope, and
        # authenticaing users on consumers is also incredibly awkward to do.
        communicator.scope['user'] = as_user
        return communicator

    @async_to_sync
    async def test_requires_processing_permissions_to_connect(self):
        communicator = self.get_communicator(as_user=self.anonymous_user)
        connected, subprotocol = await communicator.connect()
        self.assertFalse(connected, 'Anonymous user was allowed to connect')

    @mock.patch('tracker.consumers.processing.datetime')
    @async_to_sync
    async def test_new_donation_posts_to_consumer(self, datetime_mock):
        datetime_mock.utcnow.return_value = datetime.datetime.now()
        communicator = self.get_communicator(as_user=self.user)
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected, 'Could not connect')
        await sync_to_async(eventutil.post_donation_to_postbacks)(self.donation)
        result = json.loads(await communicator.receive_from())
        expected = {
            'type': 'donation_received',
            'donation': self.serialized_donation,
            'donation_count': 1,
            'event_total': float(self.donation.amount),
            'posted_at': str(datetime_mock.utcnow()),
        }
        self.assertEqual(result['type'], expected['type'])
        self.assertEqual(result['donation'], expected['donation'])
        self.assertEqual(result['donation_count'], expected['donation_count'])
        self.assertEqual(result['event_total'], expected['event_total'])
        self.assertEqual(result['posted_at'], expected['posted_at'])

    @async_to_sync
    async def test_processing_actions_get_broadcasted(self):
        communicator = self.get_communicator(as_user=self.user)
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected, 'Could not connect')

        await sync_to_async(broadcast_processing_action)(
            self.user, self.donation, DonationProcessingActionTypes.FLAGGED
        )
        result = json.loads(await communicator.receive_from())
        expected = {
            'type': 'processing_action',
            'actor_name': self.user.username,
            'actor_id': self.user.id,
            'donation': self.serialized_donation,
            'action': DonationProcessingActionTypes.FLAGGED,
        }
        self.assertEqual(result, expected)
