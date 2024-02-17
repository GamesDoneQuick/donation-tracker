from tracker import models
from tracker.api.serializers import (
    EventSerializer,
    HeadsetSerializer,
    RunnerSerializer,
    SpeedRunSerializer,
    VideoLinkSerializer,
)

from ..test_speedrun import TestSpeedRunBase
from ..util import APITestCase


class TestRunViewSet(TestSpeedRunBase, APITestCase):
    model_name = 'speedrun'
    view_user_permissions = ['can_view_tech_notes']

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.locked_user)

    def test_detail(self):
        with self.subTest('normal detail'):
            serialized = SpeedRunSerializer(self.run1)
            data = self.get_detail(self.run1)
            self.assertEqual(serialized.data, data)
            serialized = SpeedRunSerializer(self.run1, event_pk=self.event.pk)
            data = self.get_detail(self.run1, kwargs={'event_pk': self.event.pk})
            self.assertEqual(data, serialized.data)

        with self.subTest('wrong event (whether event exists or not)'):
            self.get_detail(
                self.run1, kwargs={'event_pk': self.event.pk + 1}, status_code=404
            )

        with self.subTest('permissions checks'):
            self.get_detail(
                self.run1, data={'tech_notes': ''}, user=None, status_code=403
            )

    def test_list(self):
        with self.subTest('normal lists'):
            serialized = SpeedRunSerializer(
                models.SpeedRun.objects.filter(event=self.event), many=True
            )
            data = self.get_list()
            self.assertEqual(data['results'], serialized.data)

            serialized = SpeedRunSerializer(
                models.SpeedRun.objects.filter(event=self.event),
                event_pk=self.event.pk,
                many=True,
            )
            data = self.get_list(kwargs={'event_pk': self.event.pk})
            self.assertEqual(data['results'], serialized.data)

        with self.subTest('requesting tech notes'):
            serialized = SpeedRunSerializer(
                models.SpeedRun.objects.filter(event=self.event),
                with_permissions=('tracker.can_view_tech_notes',),
                with_tech_notes=True,
                many=True,
            )
            data = self.get_list(data={'tech_notes': ''})
            self.assertEqual(data['results'], serialized.data)

        with self.subTest('permissions checks'):
            self.get_list(data={'tech_notes': ''}, user=None, status_code=403)

        with self.subTest('not a real event'):
            self.get_list(kwargs={'event_pk': self.event.pk + 100}, status_code=404)


class TestRunSerializer(TestSpeedRunBase, APITestCase):
    def _format_run(self, run, *, with_event=True, with_tech_notes=False):
        data = {
            'type': 'speedrun',
            'id': run.id,
            'name': run.name,
            'display_name': run.display_name,
            'twitch_name': run.twitch_name,
            'commentators': HeadsetSerializer(run.commentators, many=True).data,
            'run_time': run.run_time,
            'order': run.order,
            'hosts': HeadsetSerializer(run.hosts, many=True).data,
            'endtime': run.endtime,
            'category': run.category,
            'coop': run.coop,
            'onsite': run.onsite,
            'runners': RunnerSerializer(run.runners, many=True).data,
            'description': run.description,
            'console': run.console,
            'release_year': run.release_year,
            'starttime': run.starttime,
            'anchor_time': run.anchor_time,
            'setup_time': run.setup_time,
            'video_links': VideoLinkSerializer(run.video_links, many=True).data,
        }
        if with_event:
            data['event'] = EventSerializer(run.event).data
        if with_tech_notes:
            data['tech_notes'] = run.tech_notes
        return data

    def test_single(self):
        with self.subTest('public view'):
            serialized = SpeedRunSerializer(self.run1)
            self.assertV2ModelPresent(self._format_run(self.run1), serialized.data)

        with self.subTest('tech notes'):
            serialized = SpeedRunSerializer(
                self.run1,
                with_permissions=('tracker.can_view_tech_notes',),
                with_tech_notes=True,
            )
            self.assertV2ModelPresent(
                self._format_run(self.run1, with_tech_notes=True), serialized.data
            )

        with self.subTest('without event'):
            serialized = SpeedRunSerializer(self.run1, event_pk=self.event.id)
            self.assertV2ModelPresent(
                self._format_run(self.run1, with_event=False), serialized.data
            )
