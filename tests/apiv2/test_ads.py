import random

from tests import randgen
from tracker import models
from tracker.api.serializers import AdSerializer

from .test_interstitials import InterstitialTestCase


class TestAd(InterstitialTestCase):
    model_name = 'ad'
    serializer_class = AdSerializer
    rand = random.Random()

    def setUp(self):
        super().setUp()
        self.ad = randgen.generate_ad(self.rand, run=self.run)
        self.ad.save()

    def test_fetch(self):
        with self.subTest('happy path'), self.saveSnapshot():
            data = self.get_list(user=self.view_user)
            self.assertV2ModelPresent(self.ad, data)

            data = self.get_list(kwargs={'event_pk': self.event.pk})
            self.assertV2ModelPresent(self.ad, data)

            data = self.get_detail(self.ad)
            self.assertV2ModelPresent(self.ad, data)

        with self.subTest('blank event'):
            data = self.get_list(kwargs={'event_pk': self.archived_event.pk})
            self.assertEqual(data['count'], 0)

        with self.subTest('unauthenticated'):
            self.get_list(user=None, status_code=403)
            self.get_detail(self.ad, user=None, status_code=403)

    def test_create(self):
        with (
            self.subTest('happy path with ids'),
            self.saveSnapshot(),
            self.assertLogsChanges(3),
        ):
            data = self.post_new(
                data={
                    'event': self.event.pk,
                    'order': self.run.order,
                    'suborder': 'last',
                    'sponsor_name': 'Contoso',
                    'ad_name': 'Contoso University',
                    'ad_type': 'IMAGE',
                    'filename': 'foobar.jpg',
                    'length': '30',
                },
                user=self.add_user,
            )
            result = models.Ad.objects.get(id=data['id'])
            self.assertV2ModelPresent(result, data)

            data = self.post_new(
                data={
                    'anchor': self.run.pk,
                    'suborder': result.suborder + 1,
                    'sponsor_name': 'Contoso',
                    'ad_name': 'Contoso University 2',
                    'ad_type': 'IMAGE',
                    'filename': 'foobar_2.jpg',
                    'tags': ['test'],
                    'length': '30',
                }
            )
            result = models.Ad.objects.get(id=data['id'])
            self.assertV2ModelPresent(result, data)

            data = self.post_new(
                data={
                    'event': self.event.pk,
                    'order': 50,
                    'suborder': 'last',
                    'sponsor_name': 'Outer Space',
                    'ad_name': 'Orion',
                    'ad_type': 'IMAGE',
                    'filename': 'foobar_3.jpg',
                    'tags': [],
                    'length': '30',
                }
            )
            result = models.Ad.objects.get(id=data['id'])
            self.assertV2ModelPresent(result, data)
            self.assertEqual(result.suborder, 1)

        with (
            self.subTest('happy path with natural keys'),
            self.saveSnapshot(),
            self.assertLogsChanges(2),
        ):
            data = self.post_new(
                data={
                    'event': self.event.natural_key(),
                    'order': self.run.order,
                    'suborder': 'last',
                    'sponsor_name': 'Contoso',
                    'ad_name': 'Contoso University Natural',
                    'ad_type': 'IMAGE',
                    'filename': 'foobar.jpg',
                    'length': '30',
                },
                user=self.add_user,
            )
            result = models.Ad.objects.get(id=data['id'])
            self.assertV2ModelPresent(result, data)

            data = self.post_new(
                data={
                    'anchor': self.run.natural_key(),
                    'suborder': result.suborder + 1,
                    'sponsor_name': 'Contoso',
                    'ad_name': 'Contoso University 2 Natural',
                    'ad_type': 'IMAGE',
                    'filename': 'foobar_2.jpg',
                    'tags': ['test'],
                    'length': '30',
                }
            )
            result = models.Ad.objects.get(id=data['id'])
            self.assertV2ModelPresent(result, data)

    def test_patch(self):
        with self.subTest('happy path'), self.saveSnapshot(), self.assertLogsChanges(2):
            data = self.patch_detail(
                self.ad,
                data={
                    'sponsor_name': 'Still Contoso',
                },
                user=self.add_user,
            )
            self.assertV2ModelPresent(self.ad, data)

            self.patch_detail(
                self.ad,
                data={
                    'sponsor_name': 'Also Still Contoso',
                },
                kwargs={'event_pk': self.event.pk},
            )

        with self.subTest('wrong event'):
            self.patch_detail(
                self.ad,
                kwargs={'event_pk': self.blank_event.pk},
                status_code=404,
            )
