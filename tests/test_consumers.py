import datetime
import json
import random
from decimal import Decimal
from unittest import mock

from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import Permission, User
from django.test import SimpleTestCase, TransactionTestCase

from tracker import eventutil, models
from tracker.api.serializers import DonationSerializer
from tracker.api.views.donations import DonationProcessingActionTypes
from tracker.consumers import DonationConsumer, PingConsumer
from tracker.consumers.processing import ProcessingConsumer, broadcast_processing_action
from tracker.util import utcnow

from . import randgen
from .util import today_noon


class TestPingConsumer(SimpleTestCase):
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
        self.choice = models.Bid.objects.create(event=self.event, allowuseroptions=True)
        self.option = models.Bid.objects.create(parent=self.choice, istarget=True)
        self.pending = models.Bid.objects.create(
            parent=self.choice, istarget=True, state='PENDING'
        )
        self.challenge_bid = models.DonationBid.objects.create(
            donation=self.donation, bid=self.challenge, amount=0.5
        )
        self.option_bid = models.DonationBid.objects.create(
            donation=self.donation, bid=self.option, amount=0.5
        )
        self.pending_bid = models.DonationBid.objects.create(
            donation=self.donation, bid=self.pending, amount=0.5
        )

    def tearDown(self):
        self.pending_bid.delete()
        self.option_bid.delete()
        self.challenge_bid.delete()
        self.pending.delete()
        self.option.delete()
        self.choice.delete()
        self.challenge.delete()
        self.donation.delete()
        self.donor.delete()
        self.event.delete()

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
            'timereceived': self.donation.timereceived.astimezone(
                self.event.timezone
            ).isoformat(),
            'comment': self.donation.comment,
            'amount': self.donation.amount,
            'donor__visibility': self.donor.visibility,
            'donor__visiblename': self.donor.visible_name(),
            'new_total': self.donation.amount,
            'domain': self.donation.domain,
            'bids': [
                {
                    'id': self.challenge.id,
                    'total': self.challenge_bid.amount,
                    'parent': None,
                    'name': self.challenge.name,
                    'goal': self.challenge.goal,
                    'state': self.challenge.state,
                    'speedrun': self.challenge.speedrun_id,
                },
                {
                    'id': self.option.id,
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
        self.rand = random.Random()
        self.user = User.objects.create(username='test')
        self.anonymous_user = User.objects.create(username='no permissions')
        self.user.user_permissions.add(
            Permission.objects.get(name='Can change donor'),
            Permission.objects.get(name='Can change donation'),
            Permission.objects.get(name='Can view donation'),
            Permission.objects.get(name='Can view all comments'),
            Permission.objects.get(name='Can view bid'),
        )

        self.donor = models.Donor.objects.create()
        self.event = models.Event.objects.create(
            receivername='Médecins Sans Frontières',
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
        self.bids = randgen.generate_bid(
            self.rand,
            event=self.event,
            min_children=2,
            max_children=2,
            allowuseroptions=True,
            state='OPENED',
        )
        self.bids[0].save()
        self.bids[1][0][0].state = 'OPENED'
        self.bids[1][0][0].save()
        self.bids[1][1][0].state = 'PENDING'
        self.bids[1][1][0].save()
        models.DonationBid.objects.create(
            bid=self.bids[1][0][0], donation=self.donation, amount=1
        )
        models.DonationBid.objects.create(
            bid=self.bids[1][1][0], donation=self.donation, amount=0.5
        )
        self.serialized_donation = DonationSerializer(
            self.donation,
            with_all_comments=True,
            with_mod_comments=True,
            with_permissions=(
                'tracker.view_comments',
                'tracker.view_donation',
                'tracker.view_bid',
            ),
        ).data

    def tearDown(self):
        self.donation.bids.all().delete()
        self.bids[0].get_descendants().delete()
        self.bids[0].delete()
        self.donation.delete()
        self.donor.delete()
        self.event.delete()

    def get_communicator(self, *, as_user):
        communicator = WebsocketCommunicator(
            ProcessingConsumer.as_asgi(), '/tracker/ws/processing/'
        )
        communicator.scope['user'] = as_user
        return communicator

    async def test_requires_processing_permissions_to_connect(self):
        communicator = self.get_communicator(as_user=self.anonymous_user)
        connected, subprotocol = await communicator.connect()
        self.assertFalse(connected, 'Anonymous user was allowed to connect')

    @mock.patch('tracker.consumers.processing.util')
    async def test_new_donation_posts_to_consumer(self, util_mock):
        util_mock.utcnow.return_value = datetime.datetime.now(datetime.timezone.utc)
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
            'posted_at': str(util_mock.utcnow()),
        }
        self.assertEqual(result['type'], expected['type'])
        self.assertEqual(result['donation'], expected['donation'])
        self.assertEqual(result['donation_count'], expected['donation_count'])
        self.assertEqual(result['event_total'], expected['event_total'])
        self.assertEqual(result['posted_at'], expected['posted_at'])

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
