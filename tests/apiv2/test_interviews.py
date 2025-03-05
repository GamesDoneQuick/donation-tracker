import random

from tests import randgen
from tracker import models
from tracker.api import messages
from tracker.api.serializers import InterviewSerializer

from .test_interstitials import InterstitialTestCase


class TestInterviews(InterstitialTestCase):
    model_name = 'interview'
    serializer_class = InterviewSerializer
    rand = random.Random()

    def setUp(self):
        super().setUp()
        self.pj = models.Talent.objects.create(name='PJ')
        self.feasel = models.Talent.objects.create(name='feasel')
        self.spikevegeta = models.Talent.objects.create(name='SpikeVegeta')
        self.puwexil = models.Talent.objects.create(name='puwexil')
        self.kffc = models.Talent.objects.create(name='Kungfufruitcup')
        self.brossentia = models.Talent.objects.create(name='Brossentia')
        self.frozenflygone = models.Talent.objects.create(name='frozenflygone')
        self.sent = models.Talent.objects.create(name='Sent')
        self.adef = models.Talent.objects.create(name='adef')
        self.andy = models.Talent.objects.create(name='Andy')
        self.public_interview = randgen.generate_interview(self.rand, run=self.run)
        self.public_interview.save()
        self.private_interview = randgen.generate_interview(self.rand, run=self.run)
        self.private_interview.public = False
        self.private_interview.save()

    def test_fetch(self):
        with self.subTest('happy path'), self.saveSnapshot():
            with self.subTest('public'):
                data = self.get_detail(self.public_interview)
                self.assertV2ModelPresent(self.public_interview, data)

                data = self.get_list()
                self.assertV2ModelPresent(self.public_interview, data)
                self.assertV2ModelNotPresent(self.private_interview, data)

            with self.subTest('private'):
                data = self.get_detail(self.private_interview, user=self.view_user)
                self.assertV2ModelPresent(self.private_interview, data)

                data = self.get_list(data={'all': ''})
                self.assertV2ModelPresent(self.public_interview, data)
                self.assertV2ModelPresent(self.private_interview, data)

        with self.subTest('error cases'):
            self.get_detail(self.private_interview, user=None, status_code=404)
            self.get_list(data={'all': ''}, status_code=403)

    def test_create(self):
        with self.subTest(
            'happy path with ids'
        ), self.saveSnapshot(), self.assertLogsChanges(2):
            data = self.post_new(
                data={
                    'event': self.event.id,
                    'order': self.run.order,
                    'suborder': 'last',
                    'interviewers': [self.feasel.id],
                    'subjects': [self.pj.id],
                    'topic': 'Why Are You a Chaos Elemental',
                    'length': '15:00',
                },
                user=self.add_user,
            )
            result = models.Interview.objects.get(id=data['id'])
            self.assertV2ModelPresent(result, data)

            data = self.post_new(
                data={
                    'anchor': self.run.id,
                    'suborder': data['suborder'] + 1,
                    'interviewers': [self.spikevegeta.id],
                    'subjects': [self.puwexil.id],
                    'topic': 'Why Are You an Order Elemental',
                    'length': '15:00',
                }
            )
            result = models.Interview.objects.get(id=data['id'])
            self.assertV2ModelPresent(result, data)

        with self.subTest(
            'happy path with natural keys'
        ), self.saveSnapshot(), self.assertLogsChanges(2):
            data = self.post_new(
                data={
                    'event': self.event.natural_key(),
                    'order': self.run.order,
                    'suborder': 'last',
                    'interviewers': [self.frozenflygone.name],
                    'subjects': [self.sent.name],
                    'topic': 'Why Are You a Prize Elemental',
                    'length': '15:00',
                },
                user=self.add_user,
            )
            result = models.Interview.objects.get(id=data['id'])
            self.assertV2ModelPresent(result, data)

            data = self.post_new(
                data={
                    'anchor': self.run.natural_key(),
                    'suborder': data['suborder'] + 1,
                    'interviewers': [self.kffc.name],
                    'subjects': [self.brossentia.name],
                    'topic': 'Why Are You a Punishment Elemental',
                    'length': '15:00',
                }
            )
            result = models.Interview.objects.get(id=data['id'])
            self.assertV2ModelPresent(result, data)

        with self.subTest('locked event user'), self.assertLogsChanges(1):
            self.post_new(
                data={
                    'event': self.locked_event.pk,
                    'order': 1,
                    'suborder': 1,
                    'interviewers': [self.adef.id],
                    'subjects': [self.andy.id],
                    'topic': 'Why Are You a Random Elemental',
                    'length': '15:00',
                },
                user=self.locked_user,
            )

        with self.subTest('unknown talent'):
            self.post_new(
                data={
                    'interviewers': [
                        models.Talent.objects.order_by('pk').last().pk + 1
                    ],
                    'subjects': ['total nonsense'],
                },
                status_code=400,
                expected_error_codes={
                    'interviewers': messages.INVALID_PK_CODE,
                    'subjects': messages.INVALID_NATURAL_KEY_CODE,
                },
            )

        with self.subTest('blank interviewers'):
            self.post_new(
                data={
                    'interviewers': [],
                },
                status_code=400,
                expected_error_codes={'interviewers': {'non_field_errors': 'empty'}},
            )

    def test_patch(self):
        with self.subTest('happy path'), self.saveSnapshot(), self.assertLogsChanges(2):
            data = self.patch_detail(
                self.private_interview,
                data={
                    'topic': 'Setting a new PB',
                    'interviewers': [self.brossentia.name],
                    'subjects': [self.adef.pk],
                },
                user=self.add_user,
            )
            self.assertV2ModelPresent(self.private_interview, data)

            data = self.patch_detail(
                self.private_interview,
                data={
                    'topic': 'Setting a new WR',
                },
                kwargs={'event_pk': self.event.pk},
            )
            self.assertV2ModelPresent(self.private_interview, data)

        with self.subTest('wrong event'):
            self.patch_detail(
                self.private_interview,
                kwargs={'event_pk': self.blank_event.pk},
                status_code=404,
            )

        with self.subTest('unknown talent'):
            self.patch_detail(
                self.public_interview,
                data={
                    'interviewers': [
                        models.Talent.objects.order_by('pk').last().pk + 1
                    ],
                    'subjects': ['total nonsense'],
                },
                status_code=400,
                expected_error_codes={
                    'interviewers': messages.INVALID_PK_CODE,
                    'subjects': messages.INVALID_NATURAL_KEY_CODE,
                },
            )

        with self.subTest('blank interviewers'):
            self.patch_detail(
                self.public_interview,
                data={'interviewers': []},
                status_code=400,
                expected_error_codes={'interviewers': {'non_field_errors': 'empty'}},
            )
