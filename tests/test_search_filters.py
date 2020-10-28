# TODO: really should have populated fixtures for these
import datetime
import random

from django.contrib.auth.models import User, Permission
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.test import TestCase
from tracker import models
from tracker.search_feeds import apply_feed_filter
from tracker.search_filters import run_model_query

from . import randgen
from .util import today_noon, long_ago_noon


def to_id(model):
    return model and model.id


class FiltersFeedsTestCase(TestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.locked_event = randgen.generate_event(self.rand, start_time=long_ago_noon)
        self.event = randgen.generate_event(self.rand, start_time=today_noon)
        self.event.save()
        self.runs = randgen.generate_runs(self.rand, self.event, 20, scheduled=True)
        self.event.prize_drawing_date = self.event.speedrun_set.last().endtime + datetime.timedelta(
            days=1
        )
        self.event.save()
        opened_bids = randgen.generate_bids(self.rand, self.event, 15, state='OPENED')
        self.opened_bids = opened_bids[0] + opened_bids[1]
        closed_bids = randgen.generate_bids(self.rand, self.event, 5, state='CLOSED')
        self.closed_bids = closed_bids[0] + closed_bids[1]
        hidden_bids = randgen.generate_bids(self.rand, self.event, 5, state='HIDDEN')
        self.hidden_bids = hidden_bids[0] + hidden_bids[1]
        pending_bids = randgen.generate_bids(
            self.rand, self.event, 5, parent_state='OPENED', state='PENDING'
        )
        self.opened_bids += pending_bids[0]
        self.pending_bids = pending_bids[1]
        denied_bids = randgen.generate_bids(
            self.rand, self.event, 5, parent_state='OPENED', state='DENIED'
        )
        self.opened_bids += denied_bids[0]
        self.denied_bids = denied_bids[1]
        self.accepted_prizes = randgen.generate_prizes(self.rand, self.event, 5)
        self.pending_prizes = randgen.generate_prizes(
            self.rand, self.event, 5, state='PENDING'
        )
        self.donations = randgen.generate_donations(
            self.rand,
            self.event,
            200,
            bid_targets_list=[b for b in self.opened_bids if b.istarget],
        )
        models.Donation.objects.filter(
            pk__in=(d.id for d in self.donations[:40])
        ).update(readstate='PENDING')
        models.Donation.objects.filter(
            pk__in=(d.id for d in self.donations[40:80])
        ).update(commentstate='PENDING')
        models.Donation.objects.filter(
            pk__in=(d.id for d in self.donations[80:120])
        ).update(readstate='READY')
        self.pending_donations = randgen.generate_donations(
            self.rand,
            self.event,
            50,
            domain='PAYPAL',
            transactionstate='PENDING',
            no_donor=True,
        )
        self.hidden_user = User.objects.create(username='hidden')
        self.hidden_user.user_permissions.add(
            Permission.objects.get(name='Can view hidden bids')
        )
        self.prize_user = User.objects.create(username='prize')
        self.prize_user.user_permissions.add(
            Permission.objects.get(name='Can change prize')
        )
        self.locked_user = User.objects.create(username='locked')
        self.locked_user.user_permissions.add(
            Permission.objects.get(name='Can edit locked events')
        )
        self.donation_user = User.objects.create(username='donation')
        self.donation_user.user_permissions.add(
            Permission.objects.get(name='Can view pending donations')
        )
        self.donation_user.user_permissions.add(
            Permission.objects.get(name='Can view all comments')
        )


class TestPrizeFeeds(FiltersFeedsTestCase):
    def setUp(self):
        super(TestPrizeFeeds, self).setUp()
        self.query = models.Prize.objects.all()

    def test_default_feed(self):
        actual = apply_feed_filter(self.query, 'prize', None)
        expected = self.query.filter(state='ACCEPTED')
        self.assertSetEqual(set(actual), set(expected))

    def test_all_feed_without_permission(self):
        with self.assertRaises(PermissionDenied):
            apply_feed_filter(self.query, 'prize', 'all')

    def test_all_feed(self):
        actual = apply_feed_filter(self.query, 'prize', 'all', {}, self.prize_user)
        expected = self.query
        self.assertSetEqual(set(actual), set(expected))

    def test_todraw_feed_during_event_with_date(self):
        actual = apply_feed_filter(
            self.query,
            'prize',
            'todraw',
            {'time': self.event.speedrun_set.last().endtime},
            self.prize_user,
        )
        expected = []
        self.assertSetEqual(set(actual), set(expected))

    def test_todraw_feed_after_event_with_date(self):
        actual = apply_feed_filter(
            self.query,
            'prize',
            'todraw',
            {'time': self.event.prize_drawing_date},
            self.prize_user,
        )
        expected = self.accepted_prizes
        self.assertSetEqual(set(actual), set(expected))

    def test_todraw_feed_with_expired_winner(self):
        # hasn't expired yet
        models.PrizeWinner.objects.create(
            winner=self.donations[0].donor,
            prize=self.accepted_prizes[0],
            acceptdeadline=self.event.prize_drawing_date + datetime.timedelta(days=14),
        )
        # accepted
        models.PrizeWinner.objects.create(
            winner=self.donations[0].donor,
            prize=self.accepted_prizes[1],
            acceptcount=1,
            pendingcount=0,
            acceptdeadline=self.event.prize_drawing_date + datetime.timedelta(days=12),
        )
        # no expiration
        models.PrizeWinner.objects.create(
            winner=self.donations[0].donor, prize=self.accepted_prizes[2],
        )
        # expired
        models.PrizeWinner.objects.create(
            winner=self.donations[0].donor,
            prize=self.accepted_prizes[3],
            acceptdeadline=self.event.prize_drawing_date + datetime.timedelta(days=12),
        )
        actual = apply_feed_filter(
            self.query,
            'prize',
            'todraw',
            {'time': self.event.prize_drawing_date + datetime.timedelta(days=14)},
            self.prize_user,
        )
        expected = self.accepted_prizes[3:]
        self.assertSetEqual(set(actual), set(expected))


class TestBidSearchesAndFeeds(FiltersFeedsTestCase):
    def setUp(self):
        super(TestBidSearchesAndFeeds, self).setUp()
        self.query = models.Bid.objects.all()

    def test_open_feed(self):
        actual = apply_feed_filter(self.query, 'bid', 'open')
        expected = self.query.filter(state='OPENED')
        self.assertSetEqual(set(actual), set(expected))

    def test_closed_feed(self):
        actual = apply_feed_filter(self.query, 'bid', 'closed')
        expected = self.query.filter(state='CLOSED')
        self.assertSetEqual(set(actual), set(expected))

    def test_all_feed_without_permission(self):
        with self.assertRaises(PermissionDenied):
            apply_feed_filter(self.query, 'bid', 'all')

    def test_all_feed_with_permission(self):
        actual = apply_feed_filter(self.query, 'bid', 'all', user=self.hidden_user)
        expected = self.query
        self.assertSetEqual(set(actual), set(expected))

    def test_pending_feed_without_permission(self):
        with self.assertRaises(PermissionDenied):
            apply_feed_filter(self.query, 'bid', 'pending')

    def test_pending_feed_with_permission(self):
        actual = apply_feed_filter(self.query, 'bid', 'pending', user=self.hidden_user)
        expected = self.query.filter(state='PENDING', count__gt=0)
        self.assertSetEqual(set(actual), set(expected))

    def test_public_states(self):
        for state in ['OPENED', 'CLOSED']:
            actual = run_model_query('allbids', {'state': state})
            expected = self.query.filter(state=state)
            self.assertSetEqual(set(actual), set(expected))

    def test_hidden_states_without_permission(self):
        for state in ['PENDING', 'HIDDEN', 'DENIED']:
            with self.assertRaises(PermissionDenied):
                run_model_query('allbids', {'state': state})

    def test_hidden_states_with_permission(self):
        for state in ['PENDING', 'HIDDEN', 'DENIED']:
            actual = run_model_query(
                'allbids', {'feed': 'all', 'state': state}, self.hidden_user
            )
            expected = self.query.filter(state=state)
            self.assertSetEqual(set(actual), set(expected))


class TestDonationFeeds(FiltersFeedsTestCase):
    def setUp(self):
        super(TestDonationFeeds, self).setUp()
        self.query = models.Donation.objects.all()

    def test_no_feed(self):
        actual = apply_feed_filter(self.query, 'donation', None)
        expected = self.query.filter(transactionstate='COMPLETED')
        self.assertSetEqual(set(actual), set(expected))

    def test_all_feed_without_permission(self):
        with self.assertRaises(PermissionDenied):
            apply_feed_filter(self.query, 'donation', 'all')

    def test_all_feed_with_permission(self):
        actual = apply_feed_filter(
            self.query, 'donation', 'all', user=self.donation_user
        )
        expected = self.query
        self.assertSetEqual(set(actual), set(expected))

    def test_to_process_feed_without_permission(self):
        with self.assertRaises(PermissionDenied):
            apply_feed_filter(self.query, 'donation', 'toprocess')

    def test_to_process_feed_with_permission(self):
        actual = apply_feed_filter(
            self.query, 'donation', 'toprocess', user=self.donation_user
        )
        expected = self.query.filter(Q(commentstate='PENDING') | Q(readstate='PENDING'))
        self.assertSetEqual(set(actual), set(expected))

    def test_to_read_feed_with_permission(self):
        actual = apply_feed_filter(self.query, 'donation', 'toread')
        expected = self.query.filter(Q(readstate='READY'))
        self.assertSetEqual(set(actual), set(expected))
