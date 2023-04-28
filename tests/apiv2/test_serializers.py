import random

from django.test import TransactionTestCase

from tests.randgen import generate_donation, generate_donor, generate_event
from tracker.api.serializers import DonationSerializer
from tracker.models import Donor


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

    def test_anonymous_donor_says_anonymous(self):
        self.donation.donor = generate_donor(self.rand, visibility='ANON')
        serialized = DonationSerializer(self.donation).data
        self.assertEqual(serialized['donor_name'], Donor.ANONYMOUS)

    def test_no_alias_says_anonymous(self):
        # Providing no alias sets requestedvisibility to ANON from the frontend.
        # This should probably be codified on the backend in the future.
        self.donation.requestedalias = ''
        self.donation.requestedvisibility = 'ANON'

        serialized = DonationSerializer(self.donation).data
        self.assertEqual(serialized['donor_name'], Donor.ANONYMOUS)

    def test_requestedalias_different_donor_says_requestedalias(self):
        # Ensure that the visible name tied to the donation matches what the
        # user entered, regardless of who we attribute it to internally.
        self.donation.requestedalias = 'requested by donation'
        self.donation.donor = generate_donor(
            self.rand, alias='requested by donor', visibility='ALIAS'
        )

        serialized = DonationSerializer(self.donation).data
        self.assertEqual(serialized['donor_name'], 'requested by donation')
