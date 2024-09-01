from django.urls import reverse
from rest_framework.test import APIClient

from tracker import models, settings
from tracker.api.serializers import HeadsetSerializer

from ..util import APITestCase


class TestHeadsets(APITestCase):
    model_name = 'headset'

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_authenticate(user=self.super_user)
        self.headset = models.Headset.objects.create(name='lowercase')

    def test_headset_list(self):
        headsets = [self.headset]
        serialized = self.get_paginated_response(
            headsets, HeadsetSerializer(headsets, many=True).data
        )
        response = self.client.get(reverse('tracker:api_v2:headset-list'))
        self.assertEqual(response.data['results'], serialized.data['results'])

    def test_headset_detail(self):
        response = self.client.get(
            reverse('tracker:api_v2:headset-detail', args=(self.headset.pk,))
        )
        self.assertEqual(response.data, HeadsetSerializer(self.headset).data)

    def test_nonsense_params(self):
        response = self.client.get(
            reverse('tracker:api_v2:headset-list'),
            data={'limit': settings.TRACKER_PAGINATION_LIMIT + 1},
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.get(
            reverse('tracker:api_v2:headset-list'), data={'limit': 'foo'}
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.get(
            reverse('tracker:api_v2:headset-list'), data={'limit': 0}
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.get(
            reverse('tracker:api_v2:headset-list'), data={'limit': -1}
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.get(
            reverse('tracker:api_v2:headset-list'), data={'offset': 'foo'}
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.get(
            reverse('tracker:api_v2:headset-list'), data={'offset': -1}
        )
        self.assertEqual(response.status_code, 400)
