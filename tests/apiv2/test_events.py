from django.urls import reverse
from rest_framework.test import APIClient

from tracker import models, settings
from tracker.api.serializers import EventSerializer

from ..util import APITestCase


class TestEvents(APITestCase):
    model_name = 'event'
    serializer_class = EventSerializer

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_authenticate(user=self.super_user)

    def test_event_list(self):
        events = models.Event.objects.with_annotations()

        with self.saveSnapshot():
            data = self.get_list()
            self.assertExactV2Models(events, data)

            data = self.get_list(data={'totals': ''})
            self.assertExactV2Models(
                events, data, serializer_kwargs={'with_totals': True}
            )

    def test_event_detail(self):
        event = models.Event.objects.with_annotations().get(id=self.event.id)
        with self.saveSnapshot():
            data = self.get_detail(event)
            self.assertV2ModelPresent(event, data)

            data = self.get_detail(event, data={'totals': ''})
            self.assertV2ModelPresent(
                event, data, serializer_kwargs={'with_totals': True}
            )

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
