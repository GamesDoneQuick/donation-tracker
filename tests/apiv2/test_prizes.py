import datetime
from datetime import timedelta

from django.contrib.auth.models import Permission, User

from tests import randgen
from tests.util import APITestCase, today_noon
from tracker import models
from tracker.api import messages
from tracker.api.serializers import PrizeSerializer


class TestPrizes(APITestCase):
    model_name = 'prize'
    serializer_class = PrizeSerializer

    def setUp(self):
        super().setUp()
        self.runs = randgen.generate_runs(self.rand, self.event, 3, ordered=True)
        self.accepted_prize = randgen.generate_prize(
            self.rand, start_run=self.runs[0], end_run=self.runs[1]
        )
        self.accepted_prize.acceptemailsent = True
        self.accepted_prize.description = 'test long description'
        self.accepted_prize.shortdescription = 'test short description'
        self.accepted_prize.save()
        self.pending_prize = randgen.generate_prize(
            self.rand, event=self.event, state='PENDING'
        )
        self.pending_prize.save()
        self.denied_prize = randgen.generate_prize(
            self.rand, event=self.event, state='DENIED'
        )
        self.denied_prize.save()
        self.flagged_prize = randgen.generate_prize(
            self.rand, event=self.event, state='FLAGGED'
        )
        self.flagged_prize.save()
        self.archived_prize = randgen.generate_prize(
            self.rand, event=self.archived_event, state='PENDING'
        )
        self.archived_prize.save()

        self.view_claim_user = User.objects.create(username='view_claim_user')
        self.view_claim_user.user_permissions.add(
            Permission.objects.get(codename='view_prizeclaim'),
            *self.view_user.user_permissions.all(),
        )

    def test_fetch(self):
        with self.saveSnapshot():
            with self.subTest('public'):
                data = self.get_list()['results']
                self.assertExactV2Models([self.accepted_prize], data)

                # TODO: more exhaustive?
                data = self.get_list(
                    kwargs={'feed': 'current'}, data={'time': self.runs[0].starttime}
                )['results']
                self.assertExactV2Models([self.accepted_prize], data)

                data = self.get_list(
                    kwargs={'feed': 'current'}, data={'run': self.runs[0].pk}
                )['results']
                self.assertExactV2Models([self.accepted_prize], data)

                with self.subTest('searches'):
                    data = self.get_list(data={'q': self.accepted_prize.name})[
                        'results'
                    ]
                    self.assertExactV2Models([self.accepted_prize], data)

                    data = self.get_list(data={'q': self.accepted_prize.description})[
                        'results'
                    ]
                    self.assertExactV2Models([self.accepted_prize], data)

                    data = self.get_list(
                        data={'q': self.accepted_prize.shortdescription}
                    )['results']
                    self.assertExactV2Models([self.accepted_prize], data)

                    data = self.get_list(data={'name': self.accepted_prize.name})[
                        'results'
                    ]
                    self.assertExactV2Models([self.accepted_prize], data)

                    data = self.get_list(data={'state': 'ACCEPTED'})['results']
                    self.assertExactV2Models([self.accepted_prize], data)

                data = self.get_detail(self.accepted_prize)
                self.assertV2ModelPresent(self.accepted_prize, data)

                data = self.get_detail(
                    self.accepted_prize, kwargs={'event_pk': self.event.pk}
                )
                self.assertV2ModelPresent(self.accepted_prize, data)

            with self.subTest('private'):
                data = self.get_list(user=self.view_user, kwargs={'feed': 'all'})[
                    'results'
                ]
                self.assertExactV2Models(
                    [
                        self.accepted_prize,
                        self.flagged_prize,
                        self.denied_prize,
                        self.pending_prize,
                        self.archived_prize,
                    ],
                    data,
                )

                data = self.get_list(
                    user=self.view_user,
                    data={'state': ['PENDING', 'DENIED', 'FLAGGED']},
                    kwargs={'event_pk': self.event.pk},
                )['results']
                self.assertExactV2Models(
                    [self.flagged_prize, self.denied_prize, self.pending_prize], data
                )

                # avoids cluttering up the other tests with extra prizes

                def _get_prize(state):
                    prize = randgen.generate_prize(self.rand, event=self.event)
                    prize.name = state
                    prize.save()
                    randgen.assign_prize_lifecycle(self.rand, prize, state)
                    return prize

                lifecycle_prizes = {
                    state: _get_prize(state)
                    for state in [
                        'pending',
                        'notify_contributor',
                        'denied',
                        'accepted',
                        # 'ready' is not separate because the only difference is the time window
                        'drawn',
                        'winner_notified',
                        'claimed',
                        'needs_shipping',
                        'shipped',
                        'completed',
                    ]
                }

                with self.subTest('lifecycle'):
                    for state, expected in [
                        (
                            'pending',
                            [self.pending_prize, lifecycle_prizes['pending']],
                        ),
                        (
                            'notify_contributor',
                            [
                                self.denied_prize,
                                lifecycle_prizes['notify_contributor'],
                            ],
                        ),
                        (
                            'denied',
                            [lifecycle_prizes['denied']],
                        ),
                        (
                            'accepted',
                            [self.accepted_prize, lifecycle_prizes['accepted']],
                        ),
                        (
                            'drawn',
                            [lifecycle_prizes['drawn']],
                        ),
                        ('winner_notified', [lifecycle_prizes['winner_notified']]),
                        (
                            'claimed',
                            [lifecycle_prizes['claimed']],
                        ),
                        ('needs_shipping', [lifecycle_prizes['needs_shipping']]),
                        (
                            'shipped',
                            [lifecycle_prizes['shipped']],
                        ),
                        ('completed', [lifecycle_prizes['completed']]),
                    ]:
                        with self.subTest(state):
                            data = self.get_list(
                                user=self.view_claim_user,
                                data={'lifecycle': state},
                                kwargs={'event_pk': self.event.pk},
                            )
                            self.assertExactV2Models(
                                models.Prize.objects.claim_annotations()
                                .time_annotation()
                                .filter(id__in=(e.id for e in expected)),
                                data,
                                serializer_kwargs={'lifecycle': True},
                            )

                    with self.subTest('multiple'):
                        data = self.get_list(
                            user=self.view_claim_user,
                            data={
                                'lifecycle': ['notify_contributor', 'claimed'],
                            },
                            kwargs={'event_pk': self.event.pk},
                        )
                        self.assertExactV2Models(
                            models.Prize.objects.claim_annotations()
                            .time_annotation()
                            .filter(
                                id__in=(
                                    e.id
                                    for e in [
                                        self.denied_prize,
                                        lifecycle_prizes['notify_contributor'],
                                        lifecycle_prizes['claimed'],
                                    ]
                                )
                            ),
                            data,
                            serializer_kwargs={'lifecycle': True},
                        )

                    with self.subTest('ready'):
                        data = self.get_list(
                            user=self.view_claim_user,
                            data={
                                'lifecycle': 'ready',
                                'time': (
                                    self.event.prize_drawing_date
                                    + datetime.timedelta(days=1)
                                ).isoformat(),
                            },
                            kwargs={'event_pk': self.event.pk},
                        )
                        self.assertExactV2Models(
                            models.Prize.objects.claim_annotations()
                            .time_annotation()
                            .filter(
                                id__in=(
                                    e.id
                                    for e in [
                                        self.accepted_prize,
                                        lifecycle_prizes['accepted'],
                                    ]
                                )
                            ),
                            data,
                            serializer_kwargs={'lifecycle': True},
                        )

                    self.event.archived = True
                    self.event.save()
                    with self.subTest('archived'):
                        data = self.get_list(
                            user=self.view_claim_user,
                            data={
                                'lifecycle': 'archived',
                            },
                            kwargs={'event_pk': self.event.pk},
                        )
                        self.assertExactV2Models(
                            models.Prize.objects.claim_annotations()
                            .time_annotation()
                            .filter(
                                id__in=(
                                    e.id
                                    for e in [
                                        self.accepted_prize,
                                        lifecycle_prizes['accepted'],
                                        lifecycle_prizes['drawn'],
                                        lifecycle_prizes['winner_notified'],
                                        lifecycle_prizes['claimed'],
                                        lifecycle_prizes['needs_shipping'],
                                        lifecycle_prizes['shipped'],
                                    ]
                                )
                            ),
                            data,
                            serializer_kwargs={'lifecycle': True},
                        )

                    self.event.archived = False
                    self.event.save()

                # TODO
                # data = self.get_list(user=self.view_winner_user, data={'include_winners': ''})
                # self.assertExactV2Models([self.accepted_prize], data, serializer_kwargs={'include_winners': True})

        with self.subTest('error cases'):
            with self.subTest('private feeds'):
                for feed in models.Prize.HIDDEN_FEEDS:
                    with self.subTest(feed):
                        self.get_list(user=None, kwargs={'feed': feed}, status_code=403)

            with self.subTest('wrong event detail'):
                self.get_detail(
                    self.accepted_prize,
                    kwargs={'event_pk': self.blank_event.pk},
                    status_code=404,
                )

            with self.subTest('private detail'):
                for prize in [
                    self.pending_prize,
                    self.denied_prize,
                    self.flagged_prize,
                ]:
                    with self.subTest(prize.state):
                        self.get_detail(prize, user=None, status_code=404)

            with self.subTest('private states'):
                for state in models.Prize.HIDDEN_STATES:
                    with self.subTest(state):
                        self.get_list(user=None, data={'state': state}, status_code=403)

            with self.subTest('invalid lifecycle'):
                self.get_list(
                    user=self.view_claim_user,
                    data={'lifecycle': 'nonsense'},
                    status_code=400,
                )

            with self.subTest('lifecycle without permission'):
                self.get_list(
                    user=None, data={'lifecycle': 'anything'}, status_code=403
                )

            with self.subTest('combining feed and state'):
                self.get_list(
                    data={'state': 'ACCEPTED'},
                    kwargs={'feed': 'public'},
                    status_code=400,
                )

            with self.subTest('combining feed and detail'):
                self.get_detail(
                    self.accepted_prize, kwargs={'feed': 'public'}, status_code=404
                )

    def test_create(self):
        with self.saveSnapshot(), self.assertLogsChanges(4):
            with self.subTest('minimal'):
                data = self.post_new(
                    user=self.add_user,
                    data={'event': self.event.pk, 'name': 'Event Wide Prize'},
                )
                prize = models.Prize.objects.get(pk=data['id'])
                serialized = PrizeSerializer(prize)
                self.assertEqual(data, serialized.data)
                self.assertEqual(prize.handler, self.add_user)

                data = self.post_new(
                    user=self.add_user,
                    data={
                        'event': self.event.pk,
                        'name': 'Timed Prize',
                        'starttime': today_noon,
                        'endtime': today_noon + timedelta(hours=1),
                    },
                )
                serialized = PrizeSerializer(models.Prize.objects.get(pk=data['id']))
                self.assertEqual(data, serialized.data)

                data = self.post_new(
                    user=self.add_user,
                    data={
                        'event': self.event.pk,
                        'name': 'Block Prize',
                        'startrun': self.runs[0].pk,
                        'endrun': self.runs[2].pk,
                    },
                )
                serialized = PrizeSerializer(models.Prize.objects.get(pk=data['id']))
                self.assertEqual(data, serialized.data)

            with self.subTest('full blown'):
                data = self.post_new(
                    user=self.add_user,
                    kwargs={'event_pk': self.event.pk},
                    data={
                        'name': 'Earthquake Pills',
                        'startrun': self.runs[0].pk,
                        'endrun': self.runs[1].pk,
                        'description': 'Why wait? Make your own earthquakes - loads of fun!',
                        'shortdescription': 'Make your own earthquakes!',
                        'image': 'https://www.example.com/image.jpg',
                        'altimage': 'https://www.example.com/thumbnail.jpg',
                        'estimatedvalue': 10,
                        'minimumbid': 25,
                        'sumdonations': True,
                        'provider': 'Coyote',
                        'creator': 'ACME',
                        'creatorwebsite': 'https://www.acme.com/',
                    },
                )
                serialized = PrizeSerializer(
                    models.Prize.objects.get(pk=data['id']), event_pk=self.event.pk
                )
                self.assertEqual(data, serialized.data)

        with self.subTest('error cases'):
            self.post_new(
                user=self.add_user,
                data={'event': self.archived_event.pk},
                status_code=403,
                expected_error_codes=messages.ARCHIVED_EVENT_CODE,
            )
            self.post_new(
                user=self.view_user,
                status_code=403,
                expected_error_codes=messages.PERMISSION_DENIED_CODE,
            )
            self.post_new(
                user=None,
                status_code=403,
                expected_error_codes=messages.NOT_AUTHENTICATED_CODE,
            )

    def test_patch(self):
        with self.saveSnapshot(), self.assertLogsChanges(1):
            data = self.patch_detail(
                self.pending_prize, user=self.add_user, data={'state': 'ACCEPTED'}
            )
            self.assertEqual(self.pending_prize.state, 'ACCEPTED')
            self.assertEqual(data, PrizeSerializer(self.pending_prize).data)

        with self.subTest('error cases'):
            self.patch_detail(
                self.accepted_prize,
                data={'event': self.blank_event.pk},
                status_code=400,
                expected_error_codes=messages.EVENT_READ_ONLY_CODE,
            )
            self.patch_detail(
                self.archived_prize,
                user=self.add_user,
                status_code=403,
                expected_error_codes=messages.ARCHIVED_EVENT_CODE,
            )
            self.patch_detail(
                self.accepted_prize,
                user=self.view_user,
                status_code=403,
                expected_error_codes='permission_denied',
            )
            self.patch_detail(
                self.accepted_prize,
                user=None,
                status_code=403,
                expected_error_codes=messages.NOT_AUTHENTICATED_CODE,
            )
