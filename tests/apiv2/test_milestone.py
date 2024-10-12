from tests.util import APITestCase
from tracker import models
from tracker.api.serializers import MilestoneSerializer


class TestMilestoneAPI(APITestCase):
    model_name = 'milestone'
    serializer_class = MilestoneSerializer

    def _format_milestone(self, milestone, with_event=True):
        return {
            'type': 'milestone',
            'id': milestone.id,
            'amount': milestone.amount,
            **({'event': milestone.event_id} if with_event else {}),
            'description': milestone.description,
            'short_description': milestone.short_description,
            'start': milestone.start,
            'name': milestone.name,
            'visible': milestone.visible,
        }

    def setUp(self):
        super().setUp()
        self.public_milestone = models.Milestone.objects.create(
            event=self.event, name='Public Milestone', amount=500.0, visible=True
        )
        self.hidden_milestone = models.Milestone.objects.create(
            event=self.event, name='Hidden Milestone', amount=1500.0, visible=False
        )

    def test_serializer(self):
        data = MilestoneSerializer(self.public_milestone).data
        self.assertV2ModelPresent(
            self._format_milestone(self.public_milestone),
            data,
        )
        data = MilestoneSerializer(self.public_milestone, event_pk=self.event).data
        self.assertV2ModelPresent(
            self._format_milestone(self.public_milestone, with_event=False),
            data,
        )

    def test_detail(self):
        with self.subTest('user with permission'):
            serialized = MilestoneSerializer(self.hidden_milestone)
            data = self.get_detail(self.hidden_milestone, user=self.view_user)
            self.assertV2ModelPresent(serialized.data, data)

        with self.subTest('user without permission'):
            self.get_detail(self.hidden_milestone, status_code=404, user=None)
            serialized = MilestoneSerializer(self.public_milestone)
            data = self.get_detail(self.public_milestone)
            self.assertV2ModelPresent(serialized.data, data)

    def test_list(self):
        with self.subTest('user with permission'):
            data = self.get_list(user=self.view_user)['results']
            self.assertV2ModelPresent(self.public_milestone, data)
            self.assertV2ModelNotPresent(self.hidden_milestone, data)
            data = self.get_list(data={'all': ''})['results']
            self.assertV2ModelPresent(self.public_milestone, data)
            self.assertV2ModelPresent(self.hidden_milestone, data)

        with self.subTest('user without permission'):
            data = self.get_list(user=None)['results']
            self.assertV2ModelPresent(self.public_milestone, data)
            self.assertV2ModelNotPresent(self.hidden_milestone, data)
            event_data = self.get_list(kwargs={'event_pk': self.event.pk})['results']
            self.assertV2ModelPresent(
                MilestoneSerializer(self.public_milestone, event_pk=self.event.pk).data,
                event_data,
            )
            self.get_list(data={'all': ''}, status_code=403)

        with self.subTest('empty event'):
            data = self.get_list(kwargs={'event_pk': self.locked_event.pk})
            self.assertEqual(data['count'], 0, 'List was not empty')

    def test_create(self):
        with self.subTest('user with normal permission'):
            data = self.post_new(
                data={
                    'name': 'New Milestone',
                    'event': self.event.pk,
                    'amount': 1000,
                },
                user=self.add_user,
            )
            self.assertV2ModelPresent(
                MilestoneSerializer(models.Milestone.objects.get(id=data['id'])).data,
                data,
            )

            data = self.post_new(
                data={
                    'name': 'New Milestone 2',
                    'amount': 1250,
                },
                kwargs={'event_pk': self.event.pk},
            )
            self.assertV2ModelPresent(
                MilestoneSerializer(
                    models.Milestone.objects.get(id=data['id']), event_pk=data['id']
                ).data,
                data,
            )

            self.post_new(
                data={
                    'name': 'Locked Milestone',
                    'amount': 1000,
                    'event': self.locked_event.pk,
                },
                status_code=403,
            )

        with self.subTest('user with locked permission'):
            data = self.post_new(
                data={
                    'name': 'Locked Milestone',
                    'amount': 1000,
                    'event': self.locked_event.pk,
                },
                user=self.locked_user,
            )
            self.assertV2ModelPresent(
                MilestoneSerializer(models.Milestone.objects.get(id=data['id'])).data,
                data,
            )

        with self.subTest('anonymous user'):
            self.post_new(user=None, status_code=403)

    def test_patch(self):
        # move to locked event for testing patch
        self.hidden_milestone.event = self.locked_event
        self.hidden_milestone.save()

        with self.subTest('user with normal permission'):
            data = self.patch_detail(
                self.public_milestone, data={'amount': 750}, user=self.add_user
            )
            self.assertV2ModelPresent(
                MilestoneSerializer(self.public_milestone).data, data
            )
            self.patch_detail(
                self.public_milestone, data={'event': self.event.id}, status_code=400
            )
            self.patch_detail(
                self.hidden_milestone, data={'amount': 1250}, status_code=403
            )

        with self.subTest('user with locked permission'):
            data = self.patch_detail(
                self.hidden_milestone, data={'amount': 1250}, user=self.locked_user
            )
            self.assertV2ModelPresent(
                MilestoneSerializer(self.hidden_milestone).data, data
            )

        with self.subTest('anonymous user'):
            self.patch_detail(self.public_milestone, user=None, status_code=403)
