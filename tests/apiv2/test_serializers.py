import random

from django.test import TransactionTestCase

from tests.randgen import generate_donation, generate_donor, generate_event
from tracker.api.serializers import DonationSerializer


class TestDonationSerializer(TransactionTestCase):
    rand = random.Random()

    def setUp(self):
        super(TestDonationSerializer, self).setUp()
        self.event = generate_event(self.rand)
        self.event.save()
        self.donor = generate_donor(self.rand)
        self.donor.save()
        self.donation = generate_donation(self.rand, event=self.event, donor=self.donor)
        self.donation.save()

    def test_includes_all_public_fields(self):
        expected_fields = [
            'type',
            'id',
            'donor',
            'donor_name',
            'event',
            'domain',
            'transactionstate',
            'readstate',
            'commentstate',
            'amount',
            'currency',
            'timereceived',
            'comment',
            'commentlanguage',
            'pinned',
            'bids',
        ]

        serialized_donation = DonationSerializer(self.donation).data
        for field in expected_fields:
            self.assertIn(field, serialized_donation)

    def test_does_not_include_modcomment_without_permission(self):
        serialized_donation = DonationSerializer(self.donation).data
        self.assertNotIn('modcomment', serialized_donation)

    def test_includes_modcomment_with_permission(self):
        serialized_donation = DonationSerializer(
            self.donation, with_permissions=('tracker.change_donation',)
        ).data
        self.assertIn('modcomment', serialized_donation)
