import random

from tests import randgen
from tracker.api.serializers import InterviewSerializer
from tracker.models import Interview

from .test_interstitials import InterstitialTestCase


class TestInterviews(InterstitialTestCase):
    model_name = 'interview'
    serializer_class = InterviewSerializer
    rand = random.Random()

    def setUp(self):
        super().setUp()
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
                    'interviewers': 'feasel',
                    'subjects': 'PJ',
                    'topic': 'Why Are You a Chaos Elemental',
                    'length': '15:00',
                },
                user=self.add_user,
            )
            result = Interview.objects.get(id=data['id'])
            self.assertV2ModelPresent(result, data)

            data = self.post_new(
                data={
                    'anchor': self.run.id,
                    'suborder': data['suborder'] + 1,
                    'interviewers': 'SpikeVegeta',
                    'subjects': 'puwexil',
                    'topic': 'Why Are You an Order Elemental',
                    'length': '15:00',
                }
            )
            result = Interview.objects.get(id=data['id'])
            self.assertV2ModelPresent(result, data)

        with self.subTest(
            'happy path with natural keys'
        ), self.saveSnapshot(), self.assertLogsChanges(2):
            data = self.post_new(
                data={
                    'event': self.event.natural_key(),
                    'order': self.run.order,
                    'suborder': 'last',
                    'interviewers': 'frozenflygone',
                    'subjects': 'Sent',
                    'topic': 'Why Are You a Prize Elemental',
                    'length': '15:00',
                },
                user=self.add_user,
            )
            result = Interview.objects.get(id=data['id'])
            self.assertV2ModelPresent(result, data)

            data = self.post_new(
                data={
                    'anchor': self.run.natural_key(),
                    'suborder': data['suborder'] + 1,
                    'interviewers': 'JHobz',
                    'subjects': 'Brossentia',
                    'topic': 'Why Are You a Punishment Elemental',
                    'length': '15:00',
                }
            )
            result = Interview.objects.get(id=data['id'])
            self.assertV2ModelPresent(result, data)

        with self.subTest('locked event user'), self.assertLogsChanges(1):
            self.post_new(
                data={
                    'event': self.locked_event.pk,
                    'order': 1,
                    'suborder': 1,
                    'interviewers': 'Keizaron',
                    'subjects': 'Andy',
                    'topic': 'Why Are You a Random Elemental',
                    'length': '15:00',
                },
                user=self.locked_user,
            )

    def test_patch(self):
        with self.subTest('happy path'), self.saveSnapshot(), self.assertLogsChanges(2):
            data = self.patch_detail(
                self.private_interview,
                data={
                    'topic': 'Setting a new PB',
                },
                user=self.add_user,
            )
            self.assertV2ModelPresent(self.private_interview, data)

            self.patch_detail(
                self.private_interview,
                data={
                    'topic': 'Setting a new WR',
                },
                kwargs={'event_pk': self.event.pk},
            )

        with self.subTest('wrong event'):
            self.patch_detail(
                self.private_interview,
                kwargs={'event_pk': self.blank_event.pk},
                status_code=404,
            )
