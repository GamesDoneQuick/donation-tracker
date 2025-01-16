import random
from unittest.mock import patch

from django.test import TransactionTestCase

from tracker import models
from tracker.tasks import post_donation_to_postbacks

from . import randgen


class TestDonationTasks(TransactionTestCase):
    @patch('tracker.eventutil.post_donation_to_postbacks')
    def test_task_calls_post(self, post):
        self.rand = random.Random(None)
        event = randgen.generate_event(self.rand)
        event.save()
        donor = randgen.generate_donor(self.rand)
        donor.save()
        parent = randgen.generate_bid(
            self.rand,
            allowuseroptions=True,
            min_children=0,
            max_children=0,
            event=event,
            state='OPENED',
        )[0]
        parent.save()
        approved = randgen.generate_bid(
            self.rand, parent=parent, allow_children=False, state='OPENED'
        )[0]
        approved.save()
        pending = randgen.generate_bid(self.rand, parent=parent, state='PENDING')[0]
        pending.save()
        donation = randgen.generate_donation(self.rand, event=event, min_amount=10)
        donation.save()
        approved_bid = models.DonationBid.objects.create(
            donation=donation, bid=approved, amount=5 - donation.amount
        )
        pending_bid = models.DonationBid.objects.create(
            donation=donation, bid=pending, amount=donation.amount - 5
        )
        post_donation_to_postbacks(donation.id)
        with self.subTest('called at all'):
            post.assert_called_with(donation)

            with self.subTest('called with prefetch filter'):
                self.assertIn(approved_bid, donation.bids.all())
                self.assertIn(pending_bid, donation.bids.all())
                self.assertIn(approved_bid, post.call_args[0][0].bids.all())
                self.assertNotIn(pending_bid, post.call_args[0][0].bids.all())
