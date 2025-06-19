from tests import randgen
from tests.util import APITestCase
from tracker.api.serializers import DonorSerializer


class TestDonor(APITestCase):
    model_name = 'donor'
    serializer_class = DonorSerializer

    def _format_donor(self, donor, *, include_totals=False, event=None):
        return {
            'type': 'donor',
            'id': donor.id,
            **({'alias': donor.full_alias} if donor.visibility == 'ALIAS' else {}),
            **(
                {
                    'totals': [
                        {
                            'total': float(c.donation_total),
                            'count': c.donation_count,
                            'avg': float(c.donation_avg),
                            'max': float(c.donation_max),
                            'med': float(c.donation_med),
                            **(
                                {'event': c.event_id}
                                if c.event_id
                                else {'currency': c.currency}
                            ),
                        }
                        for c in donor.cache.all()
                        if event is None or c.event_id == event.id
                    ]
                }
                if include_totals
                else {}
            ),
        }

    def setUp(self):
        super().setUp()
        randgen.generate_runs(self.rand, self.event, 1, ordered=True)
        self.visible_donor = randgen.generate_donor(self.rand, visibility='ALIAS')
        self.visible_donor.save()
        randgen.generate_donations(
            self.rand, self.event, 5, donors=[self.visible_donor]
        )
        self.anonymous_donor = randgen.generate_donor(self.rand, visibility='ANON')
        self.anonymous_donor.save()
        randgen.generate_donations(
            self.rand, self.event, 3, donors=[self.anonymous_donor]
        )

    def test_fetch(self):
        with self.saveSnapshot():
            data = self.get_list(user=self.view_user)
            self.assertExactV2Models([self.visible_donor, self.anonymous_donor], data)

            data = self.get_list(user=self.view_user, data={'totals': ''})
            self.assertExactV2Models(
                [self.visible_donor, self.anonymous_donor],
                data,
                serializer_kwargs={'include_totals': True},
            )

            # just to assert the old version still works
            data = self.get_list(user=self.view_user, data={'include_totals': ''})
            self.assertExactV2Models(
                [self.visible_donor, self.anonymous_donor],
                data,
                serializer_kwargs={'include_totals': True},
            )

            data = self.get_list(
                user=self.view_user,
                kwargs={'event_pk': self.event.id},
                data={'totals': ''},
            )
            self.assertExactV2Models(
                [self.visible_donor, self.anonymous_donor],
                data,
                serializer_kwargs={'include_totals': True, 'event_pk': self.event.id},
            )

            data = self.get_detail(self.visible_donor, user=self.view_user)
            self.assertV2ModelPresent(self.visible_donor, data)

            data = self.get_detail(
                self.visible_donor, user=self.view_user, data={'totals': ''}
            )
            self.assertV2ModelPresent(
                self.visible_donor, data, serializer_kwargs={'include_totals': True}
            )

            data = self.get_detail(
                self.visible_donor,
                user=self.view_user,
                kwargs={'event_pk': self.event.id},
                data={'totals': ''},
            )
            self.assertV2ModelPresent(
                self.visible_donor,
                data,
                serializer_kwargs={'event_pk': self.event.id, 'include_totals': True},
            )

        data = self.get_list(
            user=self.view_user, kwargs={'event_pk': self.archived_event.id}
        )
        self.assertEmptyModels(data)

        with self.subTest('error cases'):
            with self.subTest('no donations on event'):
                self.get_detail(
                    self.visible_donor,
                    user=self.view_user,
                    kwargs={'event_pk': self.archived_event.id},
                    status_code=404,
                )

            with self.subTest('anonymous'):
                self.get_list(user=None, status_code=403)
                self.get_detail(self.visible_donor, user=None, status_code=403)

    def test_serializer(self):
        data = self._serialize_models(self.visible_donor, include_totals=True)
        formatted = self._format_donor(self.visible_donor, include_totals=True)
        # FIXME
        data['totals'] = sorted(
            data['totals'],
            key=lambda c: (c['event'], '') if 'event' in c else (-1, c['currency']),
        )
        formatted['totals'] = sorted(
            formatted['totals'],
            key=lambda c: (c['event'], '') if 'event' in c else (-1, c['currency']),
        )
        self.assertEqual(data, formatted)
        self.assertEqual(
            len(data['totals']),
            self.visible_donor.cache.count(),
            msg='Cache count did not match',
        )

        data = self._serialize_models(self.anonymous_donor)
        self.assertEqual(data, self._format_donor(self.anonymous_donor))
