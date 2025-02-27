import datetime
from typing import Iterable, List, Optional, Union

from django.db.models import F

import tracker.models.tag
from tracker import compat, models
from tracker.api import messages
from tracker.api.serializers import (
    EventSerializer,
    SpeedRunSerializer,
    TalentSerializer,
    VideoLinkSerializer,
)

from .. import randgen
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
                model.priority_tag,
                tracker.models.tag.Tag.objects.get_by_natural_key('coop'),
            )
            self.assertEqual(
                list(model.tags.all()),
                [tracker.models.tag.Tag.objects.get_by_natural_key('bonus')],
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

        with self.subTest('blank runner list'), self.assertLogsChanges(0):
            self.post_new(
                data={'runners': []},
                status_code=400,
                expected_error_codes={
                    'runners': {'non_field_errors': 'empty'},
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

        with self.subTest('blank runner list'), self.assertLogsChanges(0):
            self.patch_detail(
                self.run1,
                data={'runners': []},
                status_code=400,
                expected_error_codes={
                    'runners': {'non_field_errors': 'empty'},
                },
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


def _time_comparison(a: datetime.datetime, b: datetime.datetime):
    diff = a - b
    return f'{diff} early' if diff.total_seconds() > 0 else f'{-diff} late'


class TestRunMove(TestSpeedRunBase, APITestCase):
    model_name = 'speedrun'

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.add_user)

        self.interview = models.Interview.objects.create(
            event=self.event, topic='Test Interview', anchor=self.run3, suborder=1
        )
        self.ad = models.Ad.objects.create(
            event=self.event, ad_name='Test Ad', order=1, suborder=1
        )

    def _set_anchors(self, runs):
        models.SpeedRun.objects.filter(id__in=(r.id for r in runs)).update(
            anchor_time=F('starttime')
        )
        models.SpeedRun.objects.exclude(id__in=(r.id for r in runs)).update(
            anchor_time=None
        )
        for r in runs:
            r.refresh_from_db()
        self.run1.refresh_from_db()
        self.run2.refresh_from_db()
        self.run3.refresh_from_db()
        self.run4.refresh_from_db()
        self.run5.refresh_from_db()

    def assertResults(
        self,
        moving: models.SpeedRun,
        *,
        before: Optional[Union[models.SpeedRun, int]] = None,
        after: Optional[Union[models.SpeedRun, int]] = None,
        expected_change_count: int = 0,
        expected_logged_changes: Optional[int] = None,
        expected_error_codes: Optional[Union[dict, List[str], str, type]] = None,
        expected_status_code: Optional[int] = None,
        **kwargs,
    ):
        """
        :param moving: which Run is moving
        :param before: which Run to place this before
        :param after: which Run to place this after
        :param order: the precise order this run should have when done, though if it's too high it will
            be trimmed
        :param expected_change_count: how many models should be returned
        :param expected_logged_changes: how many change log entries should be created, defaults to 1 for expected success, or 0 for expected failure
        :param expected_error_codes: the error codes that should come back
        :param expected_status_code: the expected HTTP status (defaults to 200, or 400 if expected_error_codes is provided)
        """
        data = {}
        if expected_status_code is None:
            expected_status_code = 400 if expected_error_codes else 200
        if expected_logged_changes is None:
            expected_logged_changes = 1 if expected_status_code == 200 else 0
        if before:
            data['before'] = (
                before.id if isinstance(before, models.SpeedRun) else before
            )
        if after:
            data['after'] = after.id if isinstance(after, models.SpeedRun) else after
        if 'order' in kwargs:
            data['order'] = kwargs.pop('order')
        if kwargs:
            self.fail(f'unrecognized arguments {kwargs}')

        with self.assertLogsChanges(expected_logged_changes):
            data = self.patch_noun(
                moving,
                noun='move',
                data=data,
                expected_error_codes=expected_error_codes,
                status_code=expected_status_code,
            )
        if expected_status_code == 200:
            with self.subTest('number of changes'):
                self.assertEqual(
                    len([d for d in data if d['type'] == 'speedrun']),
                    expected_change_count,
                    msg='Number of changes was wrong',
                )
            with self.subTest('interview'):
                # old_order = self.interview.order
                self.interview.refresh_from_db()
                if self.interview.anchor:
                    self.interview.anchor.refresh_from_db()
                    self.assertEqual(
                        self.interview.order,
                        self.interview.anchor.order,
                        'Interview order mismatch',
                    )
                # TODO
                # if old_order != self.interview.order:
                #     self.assertIn(
                #         {'type': 'interstitial', 'id': self.interview.id},
                #         [
                #             {'type': i['type'], 'id': i['id']}
                #             for i in data
                #             if i['type'] == 'interstitial'
                #         ],
                #     )

    def assertRunsInOrder(
        self,
        ordered: Iterable[models.SpeedRun],
        unordered: Optional[Iterable[models.SpeedRun]] = None,
    ):
        if unordered is None:
            unordered = []
        all_runs = [*ordered, *unordered]

        self.assertNotEqual(len(all_runs), 0, msg='Run list was empty')
        # be exhaustive
        self.assertEqual(
            len(all_runs),
            models.SpeedRun.objects.filter(event=all_runs[0].event_id).count(),
            msg='Not all runs for this event were provided',
        )

        for r in all_runs:
            r.refresh_from_db()

        for a, b in compat.pairwise(all_runs):
            self.assertEqual(
                a.event_id, b.event_id, msg='Runs are from different events'
            )

        for n, (a, b) in enumerate(compat.pairwise(ordered), start=1):
            with self.subTest(f'ordered {n}: {a}, {b}'):
                self.assertEqual(
                    a.order, n, msg=f'Order was wrong {n},{a.order},{b.order}'
                )
                self.assertEqual(
                    b.order, n + 1, msg=f'Order was wrong {n},{a.order},{b.order}'
                )
                if a.order == 1:
                    self.assertEqual(
                        a.starttime,
                        a.event.datetime,
                        msg='First run does not start at event start',
                    )
                self.assertEqual(
                    a.endtime.isoformat(),
                    b.starttime.isoformat(),
                    msg=f'Run times for {a.id} and {b.id} do not match, {_time_comparison(a.endtime, b.starttime)}',
                )

        for r in unordered:
            with self.subTest(f'unordered {r}'):
                self.assertIsNone(r.order, msg='Run should have been unordered')

    def test_after_to_before(self):
        self.assertResults(self.run2, before=self.run1, expected_change_count=2)
        self.assertRunsInOrder(
            [self.run2, self.run1, self.run3, self.run5], [self.run4]
        )

    def test_after_to_after(self):
        self.assertResults(self.run3, after=self.run1, expected_change_count=2)
        self.assertRunsInOrder(
            [self.run1, self.run3, self.run2, self.run5], [self.run4]
        )

    def test_before_to_before(self):
        self.assertResults(self.run1, before=self.run3, expected_change_count=2)
        self.assertRunsInOrder(
            [self.run2, self.run1, self.run3, self.run5], [self.run4]
        )

    def test_before_to_after(self):
        self.assertResults(self.run2, after=self.run3, expected_change_count=2)
        self.assertRunsInOrder(
            [self.run1, self.run3, self.run2, self.run5], [self.run4]
        )

    def test_ordered_to_last(self):
        self.assertResults(self.run1, order='last', expected_change_count=4)
        self.assertRunsInOrder(
            [self.run2, self.run3, self.run5, self.run1], [self.run4]
        )

    def test_unordered_to_before(self):
        self.assertResults(self.run4, before=self.run2, expected_change_count=4)
        self.assertRunsInOrder([self.run1, self.run4, self.run2, self.run3, self.run5])

    def test_unordered_to_after(self):
        self.assertResults(self.run4, after=self.run2, expected_change_count=3)
        self.assertRunsInOrder([self.run1, self.run2, self.run4, self.run3, self.run5])

    def test_unordered_to_last(self):
        self.assertResults(self.run4, order='last', expected_change_count=1)
        self.assertRunsInOrder([self.run1, self.run2, self.run3, self.run5, self.run4])

    def test_remove_from_order(self):
        self.assertResults(self.run2, order=None, expected_change_count=3)
        self.assertRunsInOrder(
            [self.run1, self.run3, self.run5], [self.run2, self.run4]
        )

    def test_remove_last_run(self):
        self.assertResults(self.run5, order=None, expected_change_count=1)
        self.assertRunsInOrder(
            [self.run1, self.run2, self.run3], [self.run5, self.run4]
        )

    def test_already_removed(self):
        self.assertResults(self.run4, order=None, expected_status_code=400)

    def test_move_to_self(self):
        self.assertResults(
            self.run2,
            before=self.run2,
            expected_error_codes={'before': messages.NO_CHANGES_CODE},
            expected_status_code=400,
        )

        self.assertResults(
            self.run2,
            after=self.run2,
            expected_error_codes={'after': messages.NO_CHANGES_CODE},
            expected_status_code=400,
        )

        self.assertResults(
            self.run2,
            order=self.run2.order,
            expected_error_codes={'order': messages.NO_CHANGES_CODE},
            expected_status_code=400,
        )

        self.assertResults(
            self.run5,
            order='last',
            expected_error_codes={'order': messages.NO_CHANGES_CODE},
            expected_status_code=400,
        )

    def test_different_event(self):
        other_event = randgen.generate_event(self.rand)
        other_event.save()
        other_run = randgen.generate_runs(self.rand, other_event, 1, ordered=True)[0]
        self.assertResults(
            self.run2,
            before=other_run,
            expected_error_codes={'before': messages.SAME_EVENT_CODE},
            expected_status_code=400,
        )
        self.assertResults(
            self.run2,
            after=other_run,
            expected_error_codes={'after': messages.SAME_EVENT_CODE},
            expected_status_code=400,
        )

    def test_relative_to_unordered(self):
        self.assertResults(
            self.run1,
            before=self.run4,
            expected_error_codes={'before': messages.UNORDERED_RUN_CODE},
        )
        self.assertResults(
            self.run1,
            after=self.run4,
            expected_error_codes={'after': messages.UNORDERED_RUN_CODE},
        )

    def test_invalid_arguments(self):
        self.assertResults(
            self.run1, before=self.run2, after=self.run2, expected_error_codes='invalid'
        )
        self.assertResults(
            self.run1,
            before=self.run2,
            order=self.run2.order,
            expected_error_codes='invalid',
        )
        self.assertResults(
            self.run1,
            after=self.run2,
            order=self.run2.order,
            expected_error_codes='invalid',
        )
        self.assertResults(self.run1, expected_error_codes='invalid')
        self.assertResults(
            self.run1, before='foo', expected_error_codes={'before': 'invalid'}
        )
        self.assertResults(
            self.run1, after='foo', expected_error_codes={'after': 'invalid'}
        )
        self.assertResults(
            self.run1, order=0, expected_error_codes={'order': 'invalid'}
        )
        self.assertResults(
            self.run1, order='foo', expected_error_codes={'order': 'invalid'}
        )
        self.assertResults(
            self.run1,
            before=0xDEADBEEF,
            expected_error_codes={'before': 'not_found'},
            expected_status_code=404,
        )
        self.assertResults(
            self.run1,
            after=0xDEADBEEF,
            expected_error_codes={'after': 'not_found'},
            expected_status_code=404,
        )

    def test_too_long_for_anchor(self):
        self.run2.anchor_time = self.run2.starttime
        self.run2.save()
        self.run3.run_time = '0:15:00'
        self.run3.save()

        self.assertResults(
            self.run3,
            before=self.run1,
            expected_error_codes={'setup_time': 'invalid'},
            expected_status_code=400,
        )

    def test_anchor_interactions(self):
        self.run1.setup_time = '2:00:00'
        self.run1.save()

        run6, run7, run8 = randgen.generate_runs(self.rand, self.event, 3, ordered=True)
        run6.setup_time = '3:00:00'  # make it generous to allow for slot change
        run6.save()

        self._set_anchors([self.run2, run7])

        # otherwise we get a conflict
        self.interview.suborder = 2
        self.interview.save()

        with self.subTest('across anchor backwards'):
            # runs 1, 2, 3, 5, 6 should all update their time
            # 7 is anchored, and 8 is on the other side of the anchor

            self.assertResults(self.run3, before=self.run1, expected_change_count=5)
            self.assertRunsInOrder(
                [self.run3, self.run1, self.run2, self.run5, run6, run7, run8],
                [self.run4],
            )

        with self.subTest('across anchor forwards (directly after anchor)'):
            # run1 should adjust setup time
            # 3, 5, and 6 should adjust starttime
            # run1, 2, and 3 should change order

            self.assertResults(self.run3, after=self.run2, expected_change_count=5)
            self.assertRunsInOrder(
                [self.run1, self.run2, self.run3, self.run5, run6, run7, run8],
                [self.run4],
            )

        # doing a move where the new first run would be an anchor is not allowed
        with self.subTest('first run anchor'):
            self.assertResults(self.run1, order=None, expected_status_code=400)
            self.assertResults(self.run1, order=2, expected_status_code=400)

        self._set_anchors([self.run3, run7])

        with self.subTest('across anchor forwards'):
            # also checks moving a flex block forwards
            # 1, 6 should adjust setup time
            # 2, and 6 should adjust starttime
            # 2, 3, 5 should adjust order

            self.assertResults(self.run2, order=4, expected_change_count=5)
            self.assertRunsInOrder(
                [self.run1, self.run3, self.run5, self.run2, run6, run7, run8],
                [self.run4],
            )

    def test_close_order_hole(self):
        with self.subTest('before'):
            self.run5.order = 100
            # skip the save logic
            models.SpeedRun.objects.bulk_update([self.run5], ['order'])

            self.assertResults(self.run4, before=self.run5, expected_change_count=2)
            self.assertRunsInOrder(
                [self.run1, self.run2, self.run3, self.run4, self.run5]
            )

        with self.subTest('after'):
            self.run5.order = 100
            # skip the save logic
            models.SpeedRun.objects.bulk_update([self.run5], ['order'])

            self.assertResults(self.run4, after=self.run5, expected_change_count=2)
            self.assertRunsInOrder(
                [self.run1, self.run2, self.run3, self.run5, self.run4]
            )

        with self.subTest('effective no-op'):
            self.assertResults(self.run4, order=100, expected_status_code=400)

        with self.subTest('capped after the end'):
            self.assertResults(self.run5, order=100, expected_change_count=2)
            self.assertRunsInOrder(
                [self.run1, self.run2, self.run3, self.run4, self.run5]
            )

    def test_interstitial_anchor_required(self):
        self.assertResults(
            self.run3,
            order=None,
            expected_status_code=400,
            expected_error_codes={'interstitial': 'invalid'},
        )

    def test_suborder_collision(self):
        # interview is anchored to 3, ad is order 1, both have suborder 1
        self.assertResults(
            self.run3,
            before=self.run1,
            expected_status_code=400,
            expected_error_codes={'interstitial': 'invalid'},
        )
