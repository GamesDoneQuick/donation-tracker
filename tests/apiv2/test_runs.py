from tracker import models
from tracker.api.serializers import (
    EventSerializer,
    SpeedRunSerializer,
    TalentSerializer,
    VideoLinkSerializer,
)

from ..test_speedrun import TestSpeedRunBase
from ..util import APITestCase


class TestRunViewSet(TestSpeedRunBase, APITestCase):
    model_name = 'speedrun'
    serializer_class = SpeedRunSerializer
    view_user_permissions = ['can_view_tech_notes']

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.locked_user)

    def test_detail(self):
        with self.subTest('normal detail'), self.saveSnapshot():
            serialized = SpeedRunSerializer(self.run1)
            data = self.get_detail(self.run1)
            self.assertEqual(serialized.data, data)
            serialized = SpeedRunSerializer(self.run1, event_pk=self.event.pk)
            data = self.get_detail(self.run1, kwargs={'event_pk': self.event.pk})
            self.assertEqual(data, serialized.data)

            data = self.get_detail(self.run4)  # unordered run
            self.assertV2ModelPresent(self.run4, data)

        with self.subTest('wrong event (whether event exists or not)'):
            self.get_detail(
                self.run1, kwargs={'event_pk': self.event.pk + 1}, status_code=404
            )

        with self.subTest('permissions checks'):
            self.get_detail(
                self.run1, data={'tech_notes': ''}, user=None, status_code=403
            )
            self.get_detail(self.run4, status_code=404)

    def test_list(self):
        with self.subTest('normal lists'), self.saveSnapshot():
            serialized = SpeedRunSerializer(
                models.SpeedRun.objects.filter(event=self.event).exclude(order=None),
                many=True,
            )
            data = self.get_list()
            self.assertEqual(data['results'], serialized.data)

            serialized = SpeedRunSerializer(
                models.SpeedRun.objects.filter(event=self.event), many=True
            )
            data = self.get_list(data={'all': ''})
            self.assertEqual(data['results'], serialized.data)

            serialized = SpeedRunSerializer(
                models.SpeedRun.objects.filter(event=self.event).exclude(order=None),
                event_pk=self.event.pk,
                many=True,
            )
            data = self.get_list(kwargs={'event_pk': self.event.pk})
            self.assertEqual(data['results'], serialized.data)

        with self.subTest('requesting tech notes'), self.saveSnapshot():
            serialized = SpeedRunSerializer(
                models.SpeedRun.objects.filter(event=self.event).exclude(order=None),
                with_permissions=('tracker.can_view_tech_notes',),
                with_tech_notes=True,
                many=True,
            )
            data = self.get_list(data={'tech_notes': ''})
            self.assertEqual(data['results'], serialized.data)

        with self.subTest('permissions checks'):
            self.get_list(data={'tech_notes': ''}, user=None, status_code=403)
            self.get_list(data={'all': ''}, status_code=403)

        with self.subTest('not a real event'):
            self.get_list(kwargs={'event_pk': self.event.pk + 100}, status_code=404)

    def test_create(self):
        with self.subTest('smoke test'), self.saveSnapshot(), self.assertLogsChanges(1):
            data = self.post_new(
                data={
                    'event': self.event.pk,
                    'name': 'New Run',
                    'category': 'any%',
                    'runners': [self.runner1.pk],
                    'run_time': '15:00',
                    'setup_time': '5:00',
                }
            )
            model = models.SpeedRun.objects.get(id=data['id'])
            self.assertV2ModelPresent(model, data)

        with self.subTest(
            'full blown model w/implicit tag creation'
        ), self.saveSnapshot(), self.assertLogsChanges(1):
            last_run = (
                models.SpeedRun.objects.filter(event=self.event)
                .exclude(order=None)
                .last()
            )
            data = self.post_new(
                data={
                    'event': self.event.short,
                    'name': 'Mega Man Overclocked',
                    'display_name': 'Mega Man Overclocked',
                    'twitch_name': 'Mega Man',
                    'description': 'This run will be amazing.',
                    'category': 'any%',
                    'coop': True,
                    'onsite': 'ONSITE',
                    'console': 'NES',
                    'release_year': 1988,
                    'runners': [self.runner1.name],
                    'hosts': [self.headset1.name],
                    'commentators': [self.headset2.name],
                    'order': 'last',
                    'run_time': '15:00',
                    'setup_time': '5:00',
                    'anchor_time': last_run.endtime,
                    'tech_notes': 'This run has two players.',
                    'video_links': [
                        {'link_type': 'youtube', 'url': 'https://youtu.be/deadbeef2'}
                    ],
                    'priority_tag': 'coop',
                    'tags': ['bonus'],
                }
            )
            model = models.SpeedRun.objects.get(id=data['id'])
            self.assertV2ModelPresent(
                model,
                data,
                serializer_kwargs={
                    'with_tech_notes': True,
                    'with_permissions': ('tracker.can_view_tech_notes',),
                },
            )
            self.assertEqual(
                model.order, last_run.order + 1, msg='`last` order was incorrect'
            )
            self.assertEqual(
                model.tech_notes,
                'This run has two players.',
                msg='`tech_notes` not accepted.',
            )
            self.assertQuerySetEqual(
                models.Talent.objects.filter(id=self.runner1.id),
                model.runners.all(),
                msg='Runners were not assigned correctly',
            )
            self.assertQuerySetEqual(
                models.Talent.objects.filter(id=self.headset1.id),
                model.hosts.all(),
                msg='Hosts were not assigned correctly',
            )
            self.assertQuerySetEqual(
                models.Talent.objects.filter(id=self.headset2.id),
                model.commentators.all(),
                msg='Commentators were not assigned correctly',
            )
            link = models.VideoLink.objects.get(id=data['video_links'][0]['id'])
            self.assertEqual(link.url, 'https://youtu.be/deadbeef2')
            self.assertEqual(
                model.priority_tag, models.Tag.objects.get_by_natural_key('coop')
            )
            self.assertEqual(
                list(model.tags.all()), [models.Tag.objects.get_by_natural_key('bonus')]
            )

        with self.subTest('invalid PKs'), self.assertLogsChanges(0):
            self.post_new(
                data={
                    'event': 500,
                    'runners': [self.runner1.pk, 500],
                },
                status_code=400,
                expected_error_codes={'event': 'invalid_pk', 'runners': 'invalid_pk'},
            )

        with self.subTest('invalid NKs'), self.assertLogsChanges(0):
            self.post_new(
                data={
                    'runners': [self.runner1.name, 'JesseDoe'],
                    'hosts': [self.headset1.name, 'JohnDoe'],
                    'commentators': [self.headset2.name, 'JaneDoe'],
                    'video_links': [{'link_type': 'google_video'}],
                    'priority_tag': 'invalid tag',  # implicit creation, but fails validation
                },
                status_code=400,
                expected_error_codes={
                    'runners': 'invalid_natural_key',
                    'hosts': 'invalid_natural_key',
                    'commentators': 'invalid_natural_key',
                    'video_links': {'link_type': 'invalid_natural_key'},
                    'priority_tag': 'invalid',
                },
            )

        with self.subTest('mostly blank entry'), self.assertLogsChanges(0):
            self.post_new(
                data={'order': 'last'},
                status_code=400,
                expected_error_codes={
                    'event': 'required',
                },
            )

        with self.subTest(
            'event route smoke test'
        ), self.saveSnapshot(), self.assertLogsChanges(1):
            data = self.post_new(
                data={
                    'name': 'Extra Mario Bros',
                    'category': 'any%',
                    'run_time': '15:00',
                    'setup_time': '5:00',
                    'runners': [self.runner1.id],
                },
                kwargs={'event_pk': self.event.pk},
            )
            model = models.SpeedRun.objects.get(id=data['id'])
            self.assertV2ModelPresent(model, data)

        with self.subTest('permissions smoke tests'):
            self.post_new(data={}, status_code=403, user=None)
            self.post_new(data={}, status_code=403, user=self.view_user)
            self.post_new(
                data={'event': self.locked_event.pk},
                status_code=403,
                user=self.add_user,
            )

    def test_update(self):
        with self.subTest('smoke test'), self.saveSnapshot(), self.assertLogsChanges(1):
            data = self.patch_detail(self.run1, data={'name': 'Changed Name'})
            self.assertV2ModelPresent(self.run1, data)

        with self.subTest(
            'update with PKs'
        ), self.saveSnapshot(), self.assertLogsChanges(1):
            data = self.patch_detail(
                self.run1,
                data={
                    'runners': [self.runner1.id],
                    'hosts': [self.headset2.id],
                    'commentators': [self.headset1.id],
                },
            )
            self.assertV2ModelPresent(self.run1, data)
            self.assertQuerySetEqual(
                models.Talent.objects.filter(id=self.runner1.id),
                self.run1.runners.all(),
            )
            self.assertQuerySetEqual(
                models.Talent.objects.filter(id=self.headset2.id),
                self.run1.hosts.all(),
            )
            self.assertQuerySetEqual(
                models.Talent.objects.filter(id=self.headset1.id),
                self.run1.commentators.all(),
            )

        with self.subTest(
            'update with NKs'
        ), self.saveSnapshot(), self.assertLogsChanges(1):
            data = self.patch_detail(
                self.run1,
                data={
                    'runners': [self.runner2.name],
                    'hosts': [self.headset1.name],
                    'commentators': [self.headset2.name],
                },
            )
            self.assertV2ModelPresent(self.run1, data)
            self.assertQuerySetEqual(
                models.Talent.objects.filter(id=self.runner2.id),
                self.run1.runners.all(),
            )
            self.assertQuerySetEqual(
                models.Talent.objects.filter(id=self.headset1.id),
                self.run1.hosts.all(),
            )
            self.assertQuerySetEqual(
                models.Talent.objects.filter(id=self.headset2.id),
                self.run1.commentators.all(),
            )

        with self.subTest(
            'update with existing tag'
        ), self.saveSnapshot(), self.assertLogsChanges(1):
            data = self.patch_detail(self.run1, data={'tags': [self.tag1.name]})
            self.assertV2ModelPresent(self.run1, data)
            self.assertSetEqual(
                {self.tag1.name}, {t.name for t in self.run1.tags.all()}
            )

        with self.subTest('update with new tag'), self.assertLogsChanges(1):
            data = self.patch_detail(self.run1, data={'tags': ['brand_new']})
            self.assertV2ModelPresent(self.run1, data)
            self.assertSetEqual({'brand_new'}, {t.name for t in self.run1.tags.all()})

        with self.subTest(
            'clear everything out'
        ), self.saveSnapshot(), self.assertLogsChanges(1):
            data = self.patch_detail(
                self.run1,
                data={
                    'hosts': [],
                    'commentators': [],
                    'priority_tag': None,
                    'tags': [],
                },
            )
            self.assertV2ModelPresent(self.run1, data)
            self.assertSequenceEqual([], self.run1.hosts.all())
            self.assertSequenceEqual([], self.run1.commentators.all())
            self.assertSequenceEqual([], self.run1.tags.all())

        with self.subTest('no nested updates'), self.assertLogsChanges(0):
            self.patch_detail(
                self.run1,
                data={'video_links': []},
                status_code=400,
                expected_error_codes={'video_links': 'no_nested_updates'},
            )

        with self.subTest('permissions smoke tests'):
            self.patch_detail(self.run1, data={}, status_code=403, user=None)
            self.patch_detail(self.run1, data={}, status_code=403, user=self.view_user)
            self.patch_detail(
                self.run1,
                data={'event': self.locked_event.pk},
                status_code=403,
                user=self.add_user,
            )


class TestRunSerializer(TestSpeedRunBase, APITestCase):
    def _format_run(self, run, *, with_event=True, with_tech_notes=False):
        data = {
            'type': 'speedrun',
            'id': run.id,
            'name': run.name,
            'display_name': run.display_name,
            'twitch_name': run.twitch_name,
            'commentators': TalentSerializer(run.commentators, many=True).data,
            'run_time': run.run_time,
            'order': run.order,
            'hosts': TalentSerializer(run.hosts, many=True).data,
            'endtime': run.endtime,
            'category': run.category,
            'coop': run.coop,
            'onsite': run.onsite,
            'layout': run.layout,
            'runners': TalentSerializer(run.runners, many=True).data,
            'description': run.description,
            'console': run.console,
            'release_year': run.release_year,
            'starttime': run.starttime,
            'anchor_time': run.anchor_time,
            'setup_time': run.setup_time,
            'video_links': VideoLinkSerializer(run.video_links, many=True).data,
            'priority_tag': run.priority_tag and run.priority_tag.name,
            'tags': [t.name for t in run.tags.all()],
            'layout': run.layout,
        }
        if with_event:
            data['event'] = EventSerializer(run.event).data
        if with_tech_notes:
            data['tech_notes'] = run.tech_notes
        return data

    def test_single(self):
        self.run1.priority_tag = self.tag1
        self.run1.save()
        self.run1.tags.add(self.tag2)

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
