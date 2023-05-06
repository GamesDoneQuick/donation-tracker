import random
from datetime import datetime

from django.contrib.auth.models import User
from django.test import TransactionTestCase

from tests.randgen import generate_donation, generate_donor, generate_event
from tracker.api.serializers import DonationProcessActionSerializer, DonationSerializer
from tracker.models.donation import DonationProcessAction, DonationProcessState

rand = random.Random()


class TestDonationSerializer(TransactionTestCase):
    def setUp(self):
        super(TestDonationSerializer, self).setUp()
        self.event = generate_event(rand)
        self.event.save()
        self.donor = generate_donor(rand)
        self.donor.save()
        self.donation = generate_donation(rand, event=self.event, donor=self.donor)
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


class TestDonationProcessActionSerializer(TransactionTestCase):
    def setUp(self):
        super(TestDonationProcessActionSerializer, self).setUp()
        self.event = generate_event(rand)
        self.event.save()
        self.donor = generate_donor(rand)
        self.donor.save()
        self.donation = generate_donation(rand, event=self.event, donor=self.donor)
        self.donation.save()
        self.user = User.objects.create(username='test user')
        self.user.save()
        self.action = DonationProcessAction(
            actor=self.user,
            donation=self.donation,
            from_state=DonationProcessState.UNPROCESSED,
            to_state=DonationProcessState.FLAGGED,
            occurred_at=datetime.now(),
        )

    def test_includes_all_public_fields(self):
        expected_fields = [
            'type',
            'id',
            'actor',
            'donation_id',
            'from_state',
            'to_state',
            'occurred_at',
        ]

        serialized = DonationProcessActionSerializer(self.action).data
        for field in expected_fields:
            self.assertIn(field, serialized)

    def test_includes_donation_by_default(self):
        serialized = DonationProcessActionSerializer(self.action).data
        self.assertIn('donation', serialized)
        self.assertIn('donation_id', serialized)

    def test_removes_donation_when_not_requested(self):
        serialized = DonationProcessActionSerializer(
            self.action, with_donation=False
        ).data
        self.assertNotIn('donation', serialized)
        # donation_id stays for referencing without the full object
        self.assertIn('donation_id', serialized)

    def test_includes_originating_action_by_default(self):
        serialized = DonationProcessActionSerializer(self.action).data
        self.assertIn('originating_action', serialized)

    def test_removes_originating_action_when_not_requested(self):
        serialized = DonationProcessActionSerializer(
            self.action, with_originating_action=False
        ).data
        self.assertNotIn('originating_action', serialized)
