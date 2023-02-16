import random
from unittest.mock import patch

from django.test import TransactionTestCase

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
        donation = randgen.generate_donation(self.rand, event=event)
        donation.save()
        post_donation_to_postbacks(donation.id)
        post.assert_called_with(donation)
