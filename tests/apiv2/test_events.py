from django.urls import reverse
from rest_framework.test import APIClient

from tracker import settings
from tracker.api.serializers import EventSerializer

from ..util import APITestCase


class TestEvents(APITestCase):
    model_name = 'event'

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_authenticate(user=self.super_user)

    def test_event_list(self):
        events = [self.blank_event, self.event, self.locked_event]
        serialized = self.get_paginated_response(
            events, EventSerializer(events, many=True).data
        )
        response = self.client.get(reverse('tracker:api_v2:event-list'))
        self.assertEqual(response.data['results'], serialized.data['results'])

    def test_event_detail(self):
        response = self.client.get(
            reverse('tracker:api_v2:event-detail', args=(self.event.pk,))
        )
        self.assertEqual(response.data, EventSerializer(self.event).data)

    def test_nonsense_params(self):
        # not specific to events, but good enough
        response = self.client.get(
            reverse('tracker:api_v2:event-list'),
            data={'limit': settings.TRACKER_PAGINATION_LIMIT + 1},
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.get(
            reverse('tracker:api_v2:event-list'), data={'limit': 'foo'}
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.get(
            reverse('tracker:api_v2:event-list'), data={'limit': 0}
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.get(
            reverse('tracker:api_v2:event-list'), data={'limit': -1}
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.get(
            reverse('tracker:api_v2:event-list'), data={'offset': 'foo'}
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.get(
            reverse('tracker:api_v2:event-list'), data={'offset': -1}
        )
        self.assertEqual(response.status_code, 400)
