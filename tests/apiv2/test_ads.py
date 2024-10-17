import random

from tests import randgen
from tests.util import APITestCase
from tracker import models
from tracker.api import messages
from tracker.api.serializers import AdSerializer


class TestAd(APITestCase):
    model_name = 'ad'
    serializer_class = AdSerializer
    rand = random.Random()

    def setUp(self):
        super().setUp()
        self.run = randgen.generate_run(self.rand, event=self.event, ordered=True)
        self.run.save()
        self.ad = randgen.generate_ad(self.rand, run=self.run)
        self.ad.save()

    def test_fetch(self):
        with self.subTest('happy path'), self.saveSnapshot():
            data = self.get_list(user=self.view_user)['results']
            self.assertV2ModelPresent(self.ad, data)

            data = self.get_list(kwargs={'event_pk': self.event.pk})['results']
            self.assertV2ModelPresent(self.ad, data)

            data = self.get_detail(self.ad)
            self.assertV2ModelPresent(self.ad, data)

        with self.subTest('blank event'):
            data = self.get_list(kwargs={'event_pk': self.locked_event.pk})
            self.assertEqual(data['count'], 0)

        with self.subTest('unauthenticated'):
            self.get_list(user=None, status_code=403)
            self.get_detail(self.ad, user=None, status_code=403)

    def test_create(self):
        with self.subTest(
            'happy path with ids'
        ), self.saveSnapshot(), self.assertLogsChanges(2):
            data = self.post_new(
                data={
                    'event': self.event.pk,
                    'order': self.run.order,
                    'suborder': 'last',
                    'sponsor_name': 'Contoso',
                    'ad_name': 'Contoso University',
                    'ad_type': 'IMAGE',
                    'filename': 'foobar.jpg',
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
                }
            )
            result = models.Ad.objects.get(id=data['id'])
            self.assertV2ModelPresent(result, data)

        with self.subTest(
            'happy path with natural keys'
        ), self.saveSnapshot(), self.assertLogsChanges(2):
            data = self.post_new(
                data={
                    'event': self.event.natural_key(),
                    'order': self.run.order,
                    'suborder': 'last',
                    'sponsor_name': 'Contoso',
                    'ad_name': 'Contoso University Natural',
                    'ad_type': 'IMAGE',
                    'filename': 'foobar.jpg',
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
                }
            )
            result = models.Ad.objects.get(id=data['id'])
            self.assertV2ModelPresent(result, data)

        with self.subTest('locked event user'), self.assertLogsChanges(1):
            self.post_new(
                data={
                    'event': self.locked_event.pk,
                    'order': 1,
                    'suborder': 1,
                    'sponsor_name': 'Contoso',
                    'ad_name': 'Contoso Universtity',
                    'ad_type': 'IMAGE',
                    'filename': 'foobar_3.jpg',
                },
                user=self.locked_user,
            )

        with self.subTest('error cases'):
            self.post_new(
                data={
                    'event': self.locked_event.pk,
                },
                user=self.add_user,
                status_code=403,
            )

            self.post_new(
                data={
                    'event': self.event.pk,
                    'order': self.run.order,
                    'anchor': self.run.pk,
                },
                status_code=400,
                expected_error_codes={
                    'event': messages.ANCHOR_FIELD_CODE,
                    'order': messages.ANCHOR_FIELD_CODE,
                },
            )

            self.run.order = None
            self.run.save()

            self.post_new(
                data={
                    'anchor': self.run.pk,
                },
                status_code=400,
                expected_error_codes={'anchor': messages.INVALID_ANCHOR_CODE},
            )

            # doesn't blow up if missing/nonsense

            self.post_new(
                data={
                    'anchor': {'what': 'is this'},
                },
                status_code=400,
            )

            self.post_new(
                data={
                    'suborder': 'last',
                },
                status_code=400,
            )

            self.post_new(
                data={
                    'event': 'not_an_id',
                },
                status_code=400,
            )

            self.post_new(
                data={
                    'event': {'total': 'garbage'},
                    'suborder': 'last',
                },
                status_code=400,
            )

            self.post_new(
                data={
                    'order': {'also': 'silly'},
                    'suborder': 'last',
                },
                status_code=400,
            )

        with self.subTest('anonymous user'):
            self.post_new(user=None, status_code=403)

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
                data={},
                kwargs={'event_pk': self.blank_event.pk},
                status_code=404,
            )
