from random import Random
from typing import Optional

from django.contrib.auth.models import Permission, User
from django.utils import timezone
from rest_framework.test import APIClient

from tests.randgen import generate_donation, generate_donor
from tracker.api.serializers import DonationProcessActionSerializer
from tracker.models.donation import DonationProcessAction, DonationProcessState

from ..util import APITestCase

rand = Random()


class TestProcessActions(APITestCase):
    def setUp(self):
        super(TestProcessActions, self).setUp()
        self.client = APIClient()
        self.donor = generate_donor(rand)
        self.donor.save()
        self.donation = generate_donation(
            rand, donor=self.donor, commentstate='PENDING', readstate='PENDING'
        )
        self.donation.save()
        self.user.user_permissions.add(
            Permission.objects.get(codename='change_donation'),
        )

    def _generate_action(
        self,
        *,
        actor: User,
        from_state: DonationProcessState,
        to_state: DonationProcessState,
        originating_action: Optional[DonationProcessAction] = None,
    ):
        return DonationProcessAction.objects.create(
            actor=actor,
            donation=self.donation,
            from_state=from_state,
            to_state=to_state,
            occurred_at=timezone.now(),
            originating_action=originating_action,
        )

    def test_list_actions(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/tracker/api/v2/process_actions/')
        self.assertEqual(response.data, [])

        action = self._generate_action(
            actor=self.user,
            from_state=DonationProcessState.UNPROCESSED,
            to_state=DonationProcessState.FLAGGED,
        )
        serialized_action = DonationProcessActionSerializer(action).data
        response = self.client.get('/tracker/api/v2/process_actions/')
        self.assertEqual(response.data, [serialized_action])

    def test_list_actions_cannot_see_other_users(self):
        self._generate_action(
            actor=self.super_user,
            from_state=DonationProcessState.UNPROCESSED,
            to_state=DonationProcessState.FLAGGED,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/tracker/api/v2/process_actions/')
        self.assertEqual(response.data, [])

    def test_list_actions_super_user_can_see_all(self):
        action = self._generate_action(
            actor=self.super_user,
            from_state=DonationProcessState.UNPROCESSED,
            to_state=DonationProcessState.FLAGGED,
        )

        self.client.force_authenticate(user=self.super_user)
        serialized_action = DonationProcessActionSerializer(action).data
        response = self.client.get('/tracker/api/v2/process_actions/')
        self.assertEqual(response.data, [serialized_action])

    def test_list_actions_requires_permissions(self):
        response = self.client.get('/tracker/api/v2/process_actions/')
        self.assertEqual(response.status_code, 403)

    def test_undo(self):
        action = self._generate_action(
            actor=self.user,
            from_state=DonationProcessState.UNPROCESSED,
            to_state=DonationProcessState.FLAGGED,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/tracker/api/v2/process_actions/{action.id}/undo/'
        )
        undo_action = DonationProcessAction.objects.get(originating_action=action)
        self.assertEqual(undo_action.to_state, DonationProcessState.UNPROCESSED)

        serialized_undo = DonationProcessActionSerializer(undo_action).data
        self.assertEqual(response.data, serialized_undo)

    def test_undo_cannot_undo_anothers_action(self):
        action = self._generate_action(
            actor=self.super_user,
            from_state=DonationProcessState.UNPROCESSED,
            to_state=DonationProcessState.FLAGGED,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/tracker/api/v2/process_actions/{action.id}/undo/'
        )
        self.assertEqual(response.status_code, 403)
