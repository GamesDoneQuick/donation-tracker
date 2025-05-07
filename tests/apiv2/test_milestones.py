from tests import randgen
from tests.util import APITestCase
from tracker import models
from tracker.api import messages
from tracker.api.serializers import EventSerializer, MilestoneSerializer


class TestMilestones(APITestCase):
    model_name = 'milestone'
    serializer_class = MilestoneSerializer

    def _format_milestone(self, milestone, with_event=True):
        return {
            'type': 'milestone',
            'id': milestone.id,
            'amount': milestone.amount,
            **({'event': EventSerializer(milestone.event).data} if with_event else {}),
            'description': milestone.description,
            'short_description': milestone.short_description,
            'start': milestone.start,
            'name': milestone.name,
            'run': milestone.run_id,
            'visible': milestone.visible,
        }

    def setUp(self):
        super().setUp()
        self.run = randgen.generate_runs(self.rand, self.event, 1, ordered=True)[0]
        self.public_milestone = models.Milestone.objects.create(
            event=self.event,
            name='Public Milestone',
            amount=500.0,
            visible=True,
            run=self.run,
        )
        self.hidden_milestone = models.Milestone.objects.create(
            event=self.event, name='Hidden Milestone', amount=1500.0, visible=False
        )
        self.locked_milestone = models.Milestone.objects.create(
            event=self.locked_event, name='Locked Milestone', amount=1250, visible=False
        )

    def test_serializer(self):
        data = self._serialize_models(self.public_milestone)
        self.assertV2ModelPresent(
            self._format_milestone(self.public_milestone),
            data,
        )
        data = self._serialize_models(self.public_milestone, event_pk=self.event)
        self.assertV2ModelPresent(
            self._format_milestone(self.public_milestone, with_event=False),
            data,
        )

    def test_fetch(self):
        with self.saveSnapshot():
            with self.subTest('public'):
                serialized = MilestoneSerializer(self.public_milestone)
                data = self.get_detail(self.public_milestone)
                self.assertV2ModelPresent(serialized.data, data)
                data = self.get_list()
                self.assertV2ModelPresent(self.public_milestone, data)
                self.assertV2ModelNotPresent(self.hidden_milestone, data)
                event_data = self.get_list(kwargs={'event_pk': self.event.pk})[
                    'results'
                ]
                self.assertV2ModelPresent(
                    MilestoneSerializer(
                        self.public_milestone, event_pk=self.event.pk
                    ).data,
                    event_data,
                )

            with self.subTest('private'):
                serialized = MilestoneSerializer(self.hidden_milestone)
                data = self.get_detail(self.hidden_milestone, user=self.view_user)
                self.assertV2ModelPresent(serialized.data, data)
                data = self.get_list(data={'all': ''})
                self.assertV2ModelPresent(self.public_milestone, data)
                self.assertV2ModelPresent(self.hidden_milestone, data)

        with self.subTest('empty event'):
            data = self.get_list(kwargs={'event_pk': self.locked_event.pk})
            self.assertEqual(data['count'], 0, 'List was not empty')

        with self.subTest('error cases'):
            self.get_detail(self.hidden_milestone, status_code=404, user=None)
            self.get_list(data={'all': ''}, status_code=403)

    def test_create(self):
        with self.subTest('happy path'), self.saveSnapshot(), self.assertLogsChanges(3):
            data = self.post_new(
                data={
                    'name': 'New Milestone 2',
                    'amount': 1250,
                    'run': self.run.pk,
                },
                user=self.add_user,
                kwargs={'event_pk': self.event.pk},
            )
            self.assertV2ModelPresent(
                MilestoneSerializer(
                    models.Milestone.objects.get(id=data['id']), event_pk=data['id']
                ).data,
                data,
            )

            with self.subTest('with ids'):
                data = self.post_new(
                    data={
                        'name': 'New Milestone',
                        'event': self.event.pk,
                        'amount': 1000,
                    },
                )
                self.assertV2ModelPresent(
                    MilestoneSerializer(
                        models.Milestone.objects.get(id=data['id'])
                    ).data,
                    data,
                )

            with self.subTest('with natural keys'):
                data = self.post_new(
                    data={
                        'name': 'New Milestone 3',
                        'event': self.event.natural_key(),
                        'amount': 1750,
                    },
                    user=self.add_user,
                )
                self.assertV2ModelPresent(
                    MilestoneSerializer(
                        models.Milestone.objects.get(id=data['id'])
                    ).data,
                    data,
                )

        with self.subTest('error cases'):
            self.post_new(
                data={
                    'name': 'Locked Milestone',
                    'amount': 1000,
                    'event': self.locked_event.pk,
                },
                status_code=403,
            )
            self.post_new(
                data={
                    'name': 'Mismatched Event Milestone',
                    'amount': 100,
                    'event': self.blank_event.pk,
                    'run': self.run.pk,
                },
                status_code=400,
            )
            self.post_new(user=None, status_code=403)

        with self.subTest('user with locked permission'):
            data = self.post_new(
                data={
                    'name': 'Locked Milestone',
                    'amount': 1000,
                    'event': self.locked_event.pk,
                },
                user=self.locked_user,
            )
            result = models.Milestone.objects.get(id=data['id'])
            self.assertV2ModelPresent(
                result,
                data,
            )

    def test_patch(self):

        with self.subTest('happy path'), self.saveSnapshot(), self.assertLogsChanges(1):
            data = self.patch_detail(
                self.public_milestone, data={'amount': 750}, user=self.add_user
            )
            self.assertV2ModelPresent(self.public_milestone, data)

        with self.subTest('user with locked permission'):
            data = self.patch_detail(
                self.locked_milestone, data={'amount': 1000}, user=self.locked_user
            )
            self.assertV2ModelPresent(self.locked_milestone, data)

        with self.subTest('error cases'):
            self.patch_detail(
                self.public_milestone,
                data={'event': self.blank_event.id},
                status_code=400,
                expected_error_codes=messages.EVENT_READ_ONLY_CODE,
            )
            self.patch_detail(
                self.public_milestone,
                data={'amount': self.hidden_milestone.amount},
                status_code=400,
                expected_error_codes='unique_together',
            )
            self.patch_detail(
                self.locked_milestone,
                data={'amount': 1250},
                user=self.add_user,
                status_code=403,
                expected_error_codes=messages.UNAUTHORIZED_LOCKED_EVENT_CODE,
            )
            self.patch_detail(
                self.public_milestone,
                user=None,
                status_code=403,
                expected_error_codes=messages.NOT_AUTHENTICATED_CODE,
            )
