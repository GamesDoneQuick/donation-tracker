from unittest import SkipTest

from tests import randgen
from tests.util import APITestCase
from tracker.api import messages


class InterstitialTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.run = randgen.generate_run(self.rand, self.event, ordered=True)
        self.run.save()
        self.other_run = randgen.generate_run(self.rand, self.event, ordered=True)
        self.other_run.save()

    def test_interstitial_common(self):
        if getattr(self, 'model_name', None) is None:
            raise SkipTest
        with self.subTest('error cases'):
            self.post_new(
                data={
                    'event': self.archived_event.pk,
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
