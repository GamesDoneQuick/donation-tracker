import datetime
import random

from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient

from tracker import models, settings
from tracker.api.serializers import EventSerializer
from tracker.models import Event

from ..randgen import generate_donations, generate_donor, generate_event
from ..util import APITestCase


class TestEvents(APITestCase):
    model_name = 'event'
    serializer_class = EventSerializer

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_authenticate(user=self.super_user)

    def test_event_list(self):
        events = models.Event.objects.with_cache()

        with self.saveSnapshot():
            data = self.get_list()
            self.assertExactV2Models(events, data)

            data = self.get_list(data={'totals': ''})
            self.assertExactV2Models(
                events, data, serializer_kwargs={'with_totals': True}
            )

    def test_event_detail(self):
        event = models.Event.objects.with_cache().get(id=self.event.id)
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


class TestEventSerializer(TransactionTestCase):
    rand = random.Random()

    def setUp(self):
        super(TestEventSerializer, self).setUp()
        self.event = generate_event(self.rand)
        self.event.save()
        self.donor = generate_donor(self.rand)
        self.donor.save()
        generate_donations(
            self.rand,
            self.event,
            5,
            start_time=self.event.datetime,
            end_time=self.event.datetime + datetime.timedelta(hours=1),
        )

    def test_includes_all_public_fields(self):
        expected_fields = [
            'type',
            'id',
            'short',
            'name',
            'hashtag',
            'datetime',
            'timezone',
            'use_one_step_screening',
        ]

        serialized_event = EventSerializer(self.event).data
        for field in expected_fields:
            self.assertIn(field, serialized_event)

    def test_locked_is_alias_for_archived(self):
        self.assertFalse(EventSerializer(self.event).data['locked'])
        self.event.archived = True
        self.assertTrue(EventSerializer(self.event).data['locked'])

    def test_does_not_include_totals_fields(self):
        serialized_event = EventSerializer(self.event).data
        self.assertNotIn('amount', serialized_event)
        self.assertNotIn('donation_count', serialized_event)

    def test_includes_totals_fields_with_opt_in(self):
        event = Event.objects.with_cache().get(pk=self.event.pk)
        serialized_event = EventSerializer(event, with_totals=True).data
        self.assertIn('amount', serialized_event)
        self.assertIn('donation_count', serialized_event)
