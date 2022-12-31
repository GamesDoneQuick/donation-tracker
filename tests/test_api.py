import json

import pytz
from django.contrib.admin.models import ADDITION as LogEntryADDITION
from django.contrib.admin.models import CHANGE as LogEntryCHANGE
from django.contrib.admin.models import DELETION as LogEntryDELETION
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.test import override_settings
from django.urls import reverse

import tracker.models as models
import tracker.views.api
from tracker.serializers import TrackerSerializer

from . import randgen
from .util import APITestCase, today_noon, tomorrow_noon


def format_time(dt):
    return DjangoJSONEncoder().default(dt)


class TestGeneric(APITestCase):
    """generic cases that could apply to any class, even if they use a specific one for testing purposes"""

    def test_add_with_bad_type(self):
        request = self.factory.post('/api/v1/add', dict(type='nonsense'))
        request.user = self.super_user
        data = self.parseJSON(tracker.views.api.add(request), status_code=400)
        self.assertEqual('Malformed Parameters', data['error'])

    def test_add_with_bad_field(self):
        request = self.factory.post(
            '/api/v1/add', dict(type='run', nonsense='nonsense')
        )
        request.user = self.super_user
        data = self.parseJSON(tracker.views.api.add(request), status_code=400)
        self.assertEqual('Field does not exist', data['error'])

    @override_settings(TRACKER_PAGINATION_LIMIT=20)
    def test_search_with_offset_and_limit(self):
        event = randgen.generate_event(self.rand, today_noon)
        event.save()
        randgen.generate_runs(self.rand, event, 5)
        randgen.generate_donors(self.rand, 25)
        randgen.generate_donations(self.rand, event, 50, transactionstate='COMPLETED')
        request = self.factory.get(
            '/api/v1/search',
            dict(type='donation', offset=10, limit=10),
        )
        request.user = self.anonymous_user
        data = self.parseJSON(tracker.views.api.search(request))
        donations = models.Donation.objects.all()
        self.assertEqual(len(data), 10)
        self.assertListEqual([d['pk'] for d in data], [d.id for d in donations[10:20]])

        request = self.factory.get(
            '/api/v1/search',
            dict(type='donation', limit=30),
        )
        request.user = self.anonymous_user
        # bad request if limit is set above server config
        self.parseJSON(tracker.views.api.search(request), status_code=400)

        request = self.factory.get(
            '/api/v1/search',
            dict(type='donation', limit=-1),
        )
        request.user = self.anonymous_user
        # bad request if limit is negative
        self.parseJSON(tracker.views.api.search(request), status_code=400)

    def test_add_log(self):
        request = self.factory.post(
            '/api/v1/add',
            dict(type='runner', name='trihex', stream='https://twitch.tv/trihex'),
        )
        request.user = self.super_user
        data = self.parseJSON(tracker.views.api.add(request))
        runner = models.Runner.objects.get(pk=data[0]['pk'])
        add_entry = LogEntry.objects.order_by('-pk')[1]
        self.assertEqual(int(add_entry.object_id), runner.id)
        self.assertEqual(
            add_entry.content_type, ContentType.objects.get_for_model(models.Runner)
        )
        self.assertEqual(add_entry.action_flag, LogEntryADDITION)
        change_entry = LogEntry.objects.order_by('-pk')[0]
        self.assertEqual(int(change_entry.object_id), runner.id)
        self.assertEqual(
            change_entry.content_type, ContentType.objects.get_for_model(models.Runner)
        )
        self.assertEqual(change_entry.action_flag, LogEntryCHANGE)
        self.assertIn('Set name to "%s".' % runner.name, change_entry.change_message)
        self.assertIn(
            'Set stream to "%s".' % runner.stream, change_entry.change_message
        )

    def test_change_log(self):
        old_runner = models.Runner.objects.create(name='PJ', youtube='TheSuperSNES')
        request = self.factory.post(
            '/api/v1/edit',
            dict(
                type='runner',
                id=old_runner.id,
                name='trihex',
                stream='https://twitch.tv/trihex',
                youtube='',
            ),
        )
        request.user = self.super_user
        data = self.parseJSON(tracker.views.api.edit(request))
        runner = models.Runner.objects.get(pk=data[0]['pk'])
        entry = LogEntry.objects.order_by('pk').last()
        self.assertEqual(int(entry.object_id), runner.id)
        self.assertEqual(
            entry.content_type, ContentType.objects.get_for_model(models.Runner)
        )
        self.assertEqual(entry.action_flag, LogEntryCHANGE)
        self.assertIn(
            'Changed name from "%s" to "%s".' % (old_runner.name, runner.name),
            entry.change_message,
        )
        self.assertIn(
            'Changed stream from empty to "%s".' % runner.stream, entry.change_message
        )
        self.assertIn(
            'Changed youtube from "%s" to empty.' % old_runner.youtube,
            entry.change_message,
        )

    def test_change_log_m2m(self):
        run = models.SpeedRun.objects.create(name='Test Run', run_time='0:15:00')
        runner1 = models.Runner.objects.create(name='PJ')
        runner2 = models.Runner.objects.create(name='trihex')
        request = self.factory.post(
            '/api/v1/edit',
            dict(type='run', id=run.id, runners='%s,%s' % (runner1.name, runner2.name)),
        )
        request.user = self.super_user
        self.parseJSON(tracker.views.api.edit(request))
        entry = LogEntry.objects.order_by('pk').last()
        self.assertEqual(int(entry.object_id), run.id)
        self.assertEqual(
            entry.content_type, ContentType.objects.get_for_model(models.SpeedRun)
        )
        self.assertEqual(entry.action_flag, LogEntryCHANGE)
        self.assertIn(
            'Changed runners from empty to "%s".' % ([str(runner1), str(runner2)],),
            entry.change_message,
        )

    def test_delete_log(self):
        old_runner = models.Runner.objects.create(name='PJ', youtube='TheSuperSNES')
        request = self.factory.post(
            '/api/v1/delete', dict(type='runner', id=old_runner.id)
        )
        request.user = self.super_user
        self.parseJSON(tracker.views.api.delete(request))
        self.assertFalse(models.Runner.objects.filter(pk=old_runner.pk).exists())
        entry = LogEntry.objects.order_by('pk').last()
        self.assertEqual(int(entry.object_id), old_runner.id)
        self.assertEqual(
            entry.content_type, ContentType.objects.get_for_model(models.Runner)
        )
        self.assertEqual(entry.action_flag, LogEntryDELETION)


class TestSpeedRun(APITestCase):
    model_name = 'Speed Run'

    def setUp(self):
        super(TestSpeedRun, self).setUp()
        self.run1 = models.SpeedRun.objects.create(
            name='Test Run',
            category='test%',
            giantbomb_id=0x5EADBEEF,
            console='NES',
            run_time='0:45:00',
            setup_time='0:05:00',
            release_year=1988,
            description='Foo',
            commentators='blechy',
            order=1,
            tech_notes='This run requires an LCD with 0.58ms of lag for a skip late in the game',
            coop=True,
        )
        self.run2 = models.SpeedRun.objects.create(
            name='Test Run 2', run_time='0:15:00', setup_time='0:05:00', order=2
        )
        self.run3 = models.SpeedRun.objects.create(
            name='Test Run 3', run_time='0:20:00', setup_time='0:05:00', order=None
        )
        self.run4 = models.SpeedRun.objects.create(
            name='Test Run 4', run_time='0:05:00', setup_time='0', order=3
        )
        self.runner1 = models.Runner.objects.create(name='trihex')
        self.runner2 = models.Runner.objects.create(name='PJ')
        self.run1.runners.add(self.runner1)
        self.event2 = models.Event.objects.create(
            datetime=tomorrow_noon,
            targetamount=5,
            short='event2',
        )
        self.run5 = models.SpeedRun.objects.create(
            name='Test Run 5',
            run_time='0:05:00',
            setup_time='0',
            order=1,
            event=self.event2,
        )
        # TODO: something about resetting the timestamps to the right format idk
        self.run1.refresh_from_db()
        self.run2.refresh_from_db()
        self.run3.refresh_from_db()
        self.run4.refresh_from_db()
        self.run5.refresh_from_db()

    @classmethod
    def format_run(cls, run):
        return dict(
            fields=dict(
                canonical_url=(
                    'http://testserver' + reverse('tracker:run', args=(run.id,))
                ),
                category=run.category,
                commentators=run.commentators,
                console=run.console,
                coop=run.coop,
                deprecated_runners=run.deprecated_runners,
                description=run.description,
                display_name=run.display_name,
                endtime=format_time(run.endtime) if run.endtime else run.endtime,
                event=run.event.id,
                giantbomb_id=run.giantbomb_id,
                name=run.name,
                order=run.order,
                public=str(run),
                release_year=run.release_year,
                run_time=run.run_time,
                runners=[runner.id for runner in run.runners.all()],
                setup_time=run.setup_time,
                starttime=format_time(run.starttime)
                if run.starttime
                else run.starttime,
                twitch_name=run.twitch_name,
            ),
            model='tracker.speedrun',
            pk=run.id,
        )

    def test_get_single_run(self):
        request = self.factory.get('/api/v1/search', dict(type='run', id=self.run1.id))
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 1)
        expected = self.format_run(self.run1)
        self.assertEqual(data[0], expected)

    def test_get_event_runs(self):
        request = self.factory.get(
            '/api/v1/search', dict(type='run', event=self.run1.event_id)
        )
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 4)
        self.assertModelPresent(self.format_run(self.run1), data)
        self.assertModelPresent(self.format_run(self.run2), data)
        self.assertModelPresent(self.format_run(self.run3), data)
        self.assertModelPresent(self.format_run(self.run4), data)

    def test_get_starttime_lte(self):
        request = self.factory.get(
            '/api/v1/search',
            dict(type='run', starttime_lte=format_time(self.run2.starttime)),
        )
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 2)
        self.assertModelPresent(self.format_run(self.run1), data)
        self.assertModelPresent(self.format_run(self.run2), data)

    def test_get_starttime_gte(self):
        request = self.factory.get(
            '/api/v1/search',
            dict(type='run', starttime_gte=format_time(self.run2.starttime)),
        )
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 3)
        self.assertModelPresent(self.format_run(self.run2), data)
        self.assertModelPresent(self.format_run(self.run4), data)
        self.assertModelPresent(self.format_run(self.run5), data)

    def test_get_endtime_lte(self):
        request = self.factory.get(
            '/api/v1/search',
            dict(type='run', endtime_lte=format_time(self.run2.endtime)),
        )
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 2)
        self.assertModelPresent(self.format_run(self.run1), data)
        self.assertModelPresent(self.format_run(self.run2), data)

    def test_get_endtime_gte(self):
        request = self.factory.get(
            '/api/v1/search',
            dict(type='run', endtime_gte=format_time(self.run2.endtime)),
        )
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 3)
        self.assertModelPresent(self.format_run(self.run2), data)
        self.assertModelPresent(self.format_run(self.run4), data)
        self.assertModelPresent(self.format_run(self.run5), data)

    def test_add_with_category(self):
        request = self.factory.post(
            '/api/v1/add',
            dict(
                type='run',
                name='Added Run With Category',
                run_time='0:15:00',
                setup_time='0:05:00',
                category='100%',
            ),
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.add(request))
        self.assertEqual(len(data), 1)
        self.assertEqual(models.SpeedRun.objects.get(pk=data[0]['pk']).category, '100%')

    def test_edit_with_category(self):
        request = self.factory.post(
            '/api/v1/edit', dict(type='run', id=self.run2.id, category='100%')
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.edit(request))
        self.assertEqual(len(data), 1)
        self.assertEqual(models.SpeedRun.objects.get(pk=data[0]['pk']).category, '100%')

    def test_add_with_runners_as_ids(self):
        request = self.factory.post(
            '/api/v1/add',
            dict(
                type='run',
                name='Added Run With Runners',
                runners='%d,%d' % (self.runner1.id, self.runner2.id),
            ),
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.add(request))
        self.assertEqual(len(data), 1)
        self.assertSetEqual(
            set(models.SpeedRun.objects.get(pk=data[0]['pk']).runners.all()),
            {self.runner1, self.runner2},
        )

    def test_add_with_runners_as_invalid_ids(self):
        request = self.factory.post(
            '/api/v1/add',
            dict(
                type='run',
                name='Added Run With Runners',
                runners='%d,%d' % (self.runner1.id, 6666),
            ),
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.add(request), status_code=400)
        self.assertEqual('Foreign Key relation could not be found', data['error'])

    def test_add_with_runners_as_json_ids(self):
        request = self.factory.post(
            '/api/v1/add',
            dict(
                type='run',
                name='Added Run With Runners',
                runners=json.dumps([self.runner1.id, self.runner2.id]),
            ),
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.add(request))
        self.assertEqual(len(data), 1)
        self.assertSetEqual(
            set(models.SpeedRun.objects.get(pk=data[0]['pk']).runners.all()),
            {self.runner1, self.runner2},
        )

    def test_add_with_runners_as_names(self):
        request = self.factory.post(
            '/api/v1/add',
            dict(
                type='run',
                name='Added Run With Runners',
                runners='%s,%s'
                % (self.runner1.name.upper(), self.runner2.name.lower()),
            ),
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.add(request))
        self.assertEqual(len(data), 1)
        self.assertSetEqual(
            set(models.SpeedRun.objects.get(pk=data[0]['pk']).runners.all()),
            {self.runner1, self.runner2},
        )

    def test_add_with_runners_as_json_names(self):
        request = self.factory.post(
            '/api/v1/add',
            dict(
                type='run',
                name='Added Run With Runners',
                runners=json.dumps(
                    [self.runner1.name.upper(), self.runner2.name.lower()]
                ),
            ),
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.add(request))
        self.assertEqual(len(data), 1)
        self.assertSetEqual(
            set(models.SpeedRun.objects.get(pk=data[0]['pk']).runners.all()),
            {self.runner1, self.runner2},
        )

    def test_add_with_runners_as_json_natural_keys(self):
        request = self.factory.post(
            '/api/v1/add',
            dict(
                type='run',
                name='Added Run With Runners',
                runners=json.dumps(
                    [self.runner1.natural_key(), self.runner2.natural_key()]
                ),
            ),
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.add(request))
        self.assertEqual(len(data), 1)
        self.assertSetEqual(
            set(models.SpeedRun.objects.get(pk=data[0]['pk']).runners.all()),
            {self.runner1, self.runner2},
        )

    def test_add_with_runners_as_names_invalid(self):
        request = self.factory.post(
            '/api/v1/add',
            dict(
                type='run',
                name='Added Run With Runners',
                runners='%s,%s' % (self.runner1.name, 'nonsense'),
            ),
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.add(request), status_code=400)
        self.assertEqual('Foreign Key relation could not be found', data['error'])

    def test_edit_with_runners_as_ids(self):
        request = self.factory.post(
            '/api/v1/edit',
            dict(
                type='run',
                id=self.run2.id,
                runners='%d,%d' % (self.runner1.id, self.runner2.id),
            ),
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.edit(request))
        self.assertEqual(len(data), 1)
        self.assertSetEqual(
            set(models.SpeedRun.objects.get(pk=data[0]['pk']).runners.all()),
            {self.runner1, self.runner2},
        )

    def test_edit_with_runners_as_json_ids(self):
        request = self.factory.post(
            '/api/v1/edit',
            dict(
                type='run',
                id=self.run2.id,
                runners=json.dumps([self.runner1.id, self.runner2.id]),
            ),
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.edit(request))
        self.assertEqual(len(data), 1)
        self.assertSetEqual(
            set(models.SpeedRun.objects.get(pk=data[0]['pk']).runners.all()),
            {self.runner1, self.runner2},
        )

    def test_edit_with_runners_as_ids_invalid(self):
        request = self.factory.post(
            '/api/v1/edit',
            dict(
                type='run', id=self.run2.id, runners='%d,%d' % (self.runner1.id, 6666)
            ),
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.edit(request), status_code=400)
        self.assertEqual('Foreign Key relation could not be found', data['error'])

    def test_edit_with_runners_as_names(self):
        request = self.factory.post(
            '/api/v1/edit',
            dict(
                type='run',
                id=self.run2.id,
                runners='%s,%s'
                % (self.runner1.name.upper(), self.runner2.name.lower()),
            ),
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.edit(request))
        self.assertEqual(len(data), 1)
        self.assertSetEqual(
            set(models.SpeedRun.objects.get(pk=data[0]['pk']).runners.all()),
            {self.runner1, self.runner2},
        )

    def test_edit_with_runners_as_json_names(self):
        request = self.factory.post(
            '/api/v1/edit',
            dict(
                type='run',
                id=self.run2.id,
                runners=json.dumps(
                    [self.runner1.name.upper(), self.runner2.name.lower()]
                ),
            ),
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.edit(request))
        self.assertEqual(len(data), 1)
        self.assertSetEqual(
            set(models.SpeedRun.objects.get(pk=data[0]['pk']).runners.all()),
            {self.runner1, self.runner2},
        )

    def test_edit_with_runners_as_json_natural_keys(self):
        request = self.factory.post(
            '/api/v1/edit',
            dict(
                type='run',
                id=self.run2.id,
                runners=json.dumps(
                    [self.runner1.natural_key(), self.runner2.natural_key()]
                ),
            ),
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.edit(request))
        self.assertEqual(len(data), 1)
        self.assertSetEqual(
            set(models.SpeedRun.objects.get(pk=data[0]['pk']).runners.all()),
            {self.runner1, self.runner2},
        )

    def test_edit_with_runners_as_names_invalid(self):
        request = self.factory.post(
            '/api/v1/edit',
            dict(
                type='run',
                id=self.run2.id,
                runners='%s,%s' % (self.runner1.name, 'nonsense'),
            ),
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.edit(request), status_code=400)
        self.assertEqual('Foreign Key relation could not be found', data['error'])

    def test_tech_notes_without_permission(self):
        request = self.factory.get(
            '/api/v1/search', dict(type='run', id=self.run1.id, tech_notes='')
        )
        request.user = self.anonymous_user
        self.parseJSON(tracker.views.api.search(request), status_code=403)

    def test_tech_notes_with_permission(self):
        request = self.factory.get(
            '/api/v1/search', dict(type='run', id=self.run1.id, tech_notes='')
        )
        request.user = self.user
        self.user.user_permissions.add(
            Permission.objects.get(name='Can view tech notes')
        )
        data = self.parseJSON(tracker.views.api.search(request))
        expected = self.format_run(self.run1)
        expected['fields']['tech_notes'] = self.run1.tech_notes
        self.assertEqual(data[0], expected)


class TestRunner(APITestCase):
    model_name = 'runner'

    def setUp(self):
        super(TestRunner, self).setUp()
        self.runner1 = models.Runner.objects.create(name='lower')
        self.runner2 = models.Runner.objects.create(name='UPPER')
        self.run1 = models.SpeedRun.objects.create(
            event=self.event, order=1, run_time='5:00', setup_time='5:00'
        )
        self.run1.runners.add(self.runner1)
        self.run2 = models.SpeedRun.objects.create(
            event=self.event, order=2, run_time='5:00', setup_time='5:00'
        )
        self.run2.runners.add(self.runner1)

    @classmethod
    def format_runner(cls, runner):
        return dict(
            fields=dict(
                donor=runner.donor.visible_name() if runner.donor else None,
                public=runner.name,
                name=runner.name,
                stream=runner.stream,
                twitter=runner.twitter,
                youtube=runner.youtube,
                platform=runner.platform,
                pronouns=runner.pronouns,
            ),
            model='tracker.runner',
            pk=runner.id,
        )

    def test_name_case_insensitive_search(self):
        request = self.factory.get(
            '/api/v1/search', dict(type='runner', name=self.runner1.name.upper())
        )
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        expected = self.format_runner(self.runner1)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0], expected)

    def test_name_case_insensitive_add(self):
        request = self.factory.post(
            '/api/v1/add', dict(type='runner', name=self.runner1.name.upper())
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.add(request), status_code=400)
        self.assertRegex(data['messages'][0], 'case-insensitive.*already exists')

    def test_search_by_event(self):
        request = self.factory.get(
            '/api/v1/search', dict(type='runner', event=self.event.id)
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.search(request))
        expected = self.format_runner(self.runner1)
        # testing both that the other runner does not show up, and that this runner only shows up once
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0], expected)


class TestPrize(APITestCase):
    model_name = 'prize'

    def setUp(self):
        super(TestPrize, self).setUp()

    @classmethod
    def format_prize(cls, prize, request):
        def add_run_fields(fields, run, prefix):
            dumped_run = TrackerSerializer(models.SpeedRun, request).serialize([run])[0]
            for key, value in dumped_run['fields'].items():
                if key not in [
                    'canonical_url',
                    'endtime',
                    'name',
                    'starttime',
                    'display_name',
                    'order',
                ]:
                    continue
                try:
                    value = DjangoJSONEncoder().default(value)
                except TypeError:
                    pass
                fields[prefix + '__' + key] = value
            fields[prefix + '__public'] = str(run)

        run_fields = {}
        if prize.startrun:
            add_run_fields(run_fields, prize.startrun, 'startrun')
            add_run_fields(run_fields, prize.endrun, 'endrun')
        draw_time_fields = {}
        if prize.has_draw_time():
            draw_time_fields['start_draw_time'] = cls.encoder.default(
                prize.start_draw_time()
            )
            draw_time_fields['end_draw_time'] = cls.encoder.default(
                prize.end_draw_time()
            )

        return dict(
            fields=dict(
                allowed_prize_countries=[
                    c.id for c in prize.allowed_prize_countries.all()
                ],
                disallowed_prize_regions=[
                    r.id for r in prize.disallowed_prize_regions.all()
                ],
                public=prize.name,
                name=prize.name,
                canonical_url=(
                    request.build_absolute_uri(
                        reverse('tracker:prize', args=(prize.id,))
                    )
                ),
                category=prize.category_id,
                image=prize.image,
                altimage=prize.altimage,
                imagefile=prize.imagefile.url if prize.imagefile else '',
                description=prize.description,
                shortdescription=prize.shortdescription,
                creator=prize.creator,
                creatoremail=prize.creatoremail,
                creatorwebsite=prize.creatorwebsite,
                key_code=prize.key_code,
                provider=prize.provider,
                maxmultiwin=prize.maxmultiwin,
                maxwinners=prize.maxwinners,
                numwinners=len(prize.get_prize_winners()),
                custom_country_filter=prize.custom_country_filter,
                estimatedvalue=prize.estimatedvalue,
                minimumbid=prize.minimumbid,
                maximumbid=prize.maximumbid,
                sumdonations=prize.sumdonations,
                randomdraw=prize.randomdraw,
                event=prize.event_id,
                startrun=prize.startrun_id,
                endrun=prize.endrun_id,
                starttime=prize.starttime,
                endtime=prize.endtime,
                **run_fields,
                **draw_time_fields,
            ),
            model='tracker.prize',
            pk=prize.id,
        )

    def test_search(self):
        models.SpeedRun.objects.create(
            event=self.event,
            name='Test Run',
            run_time='5:00',
            setup_time='5:00',
            order=1,
        ).clean()
        prize = models.Prize.objects.create(
            event=self.event,
            handler=self.add_user,
            name='Prize With Image',
            state='ACCEPTED',
            startrun=self.event.speedrun_set.first(),
            endrun=self.event.speedrun_set.first(),
            image='https://example.com/example.jpg',
            maxwinners=3,
        )
        donors = randgen.generate_donors(self.rand, 3)
        models.PrizeWinner.objects.create(
            prize=prize, acceptcount=1, pendingcount=0, declinecount=0, winner=donors[0]
        )
        models.PrizeWinner.objects.create(
            prize=prize, acceptcount=0, pendingcount=1, declinecount=0, winner=donors[1]
        )
        models.PrizeWinner.objects.create(
            prize=prize, acceptcount=0, pendingcount=0, declinecount=1, winner=donors[2]
        )
        prize.refresh_from_db()
        request = self.factory.get(
            '/api/v1/search',
            dict(
                type='prize',
            ),
        )
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0], self.format_prize(prize, request))

    def test_search_with_imagefile(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        models.SpeedRun.objects.create(
            event=self.event,
            name='Test Run',
            run_time='5:00',
            setup_time='5:00',
            order=1,
        ).clean()
        prize = models.Prize.objects.create(
            event=self.event,
            handler=self.add_user,
            name='Prize With Image',
            state='ACCEPTED',
            startrun=self.event.speedrun_set.first(),
            endrun=self.event.speedrun_set.first(),
            imagefile=SimpleUploadedFile('test.jpg', b''),
        )
        prize.refresh_from_db()
        request = self.factory.get(
            '/api/v1/search',
            dict(
                type='prize',
            ),
        )
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0], self.format_prize(prize, request))

    def test_add_with_new_category(self):
        self.add_user.user_permissions.add(
            Permission.objects.get(name='Can add Prize Category')
        )
        request = self.factory.post(
            '/api/v1/add',
            dict(
                type='prize',
                name='Added Prize With Category',
                event=json.dumps(self.event.natural_key()),
                handler=json.dumps(self.add_user.natural_key()),
                category='Grand',
            ),
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.add(request))
        prize = models.Prize.objects.get(pk=data[0]['pk'])
        self.assertEqual(len(data), 1)
        # TODO: add and search don't format the same
        # self.assertEqual(data[0], self.format_prize(prize))
        self.assertEqual(
            prize.category,
            models.PrizeCategory.objects.get(name='Grand'),
        )

    def test_add_with_new_category_without_category_add_permission(self):
        request = self.factory.post(
            '/api/v1/add',
            dict(
                type='prize',
                name='Added Prize With Category',
                event=json.dumps(self.event.natural_key()),
                handler=json.dumps(self.add_user.natural_key()),
                category='Grand',
            ),
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.add(request), status_code=400)
        self.assertEqual('Foreign Key relation could not be found', data['error'])


class TestEvent(APITestCase):
    model_name = 'event'

    def setUp(self):
        super(TestEvent, self).setUp()

    def test_event_annotations(self):
        models.Donation.objects.create(
            event=self.event,
            amount=10,
            domain='PAYPAL',
            transactionstate='PENDING',
        )
        models.Donation.objects.create(event=self.event, amount=5, domainId='123457')
        # there was a bug where events with only pending donations wouldn't come back in the search
        models.Donation.objects.create(
            event=self.locked_event,
            amount=10,
            domain='PAYPAL',
            transactionstate='PENDING',
        )
        # make sure empty events show up too
        extra_event = randgen.generate_event(self.rand, today_noon)
        extra_event.save()
        request = self.factory.get('/api/v1/search', dict(type='event'))
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 3)
        self.assertModelPresent(
            {
                'pk': self.event.id,
                'model': 'tracker.event',
                'fields': {'amount': 5.0, 'count': 1, 'max': 5.0, 'avg': 5.0},
            },
            data,
            partial=True,
        )
        self.assertModelPresent(
            {
                'pk': self.locked_event.id,
                'model': 'tracker.event',
                'fields': {'amount': 0.0, 'count': 0, 'max': 0.0, 'avg': 0.0},
            },
            data,
            partial=True,
        )
        self.assertModelPresent(
            {
                'pk': extra_event.id,
                'model': 'tracker.event',
                'fields': {'amount': 0.0, 'count': 0, 'max': 0.0, 'avg': 0.0},
            },
            data,
            partial=True,
        )


class TestBid(APITestCase):
    model_name = 'bid'

    @classmethod
    def format_bid(cls, bid, request):
        def add_run_fields(fields, run, prefix):
            dumped_run = TrackerSerializer(models.SpeedRun, request).serialize([run])[0]
            for key, value in dumped_run['fields'].items():
                if key not in [
                    'canonical_url',
                    'endtime',
                    'name',
                    'starttime',
                    'display_name',
                    'twitch_name',
                    'order',
                ]:
                    continue
                try:
                    value = DjangoJSONEncoder().default(value)
                except TypeError:
                    pass
                fields[prefix + '__' + key] = value
            fields[prefix + '__public'] = str(run)

        def add_parent_fields(fields, parent, prefix):
            dumped_bid = TrackerSerializer(models.Bid, request).serialize([parent])[0]
            for key, value in dumped_bid['fields'].items():
                if key not in [
                    'canonical_url',
                    'name',
                    'state',
                    'goal',
                    'allowuseroptions',
                    'option_max_length',
                    'total',
                    'count',
                ]:
                    continue
                try:
                    value = DjangoJSONEncoder().default(value)
                except TypeError:
                    pass
                fields[prefix + '__' + key] = value
            fields[prefix + '__public'] = str(parent)
            add_event_fields(fields, parent.event, prefix + '__event')

        def add_event_fields(fields, event, prefix):
            dumped_event = TrackerSerializer(models.Event, request).serialize([event])[
                0
            ]
            for key, value in dumped_event['fields'].items():
                if key not in ['canonical_url', 'name', 'short', 'timezone']:
                    continue
                try:
                    value = DjangoJSONEncoder().default(value)
                except TypeError:
                    pass
                fields[prefix + '__' + key] = value
            fields[prefix + '__datetime'] = DjangoJSONEncoder().default(
                event.datetime.astimezone(pytz.utc)
            )
            fields[prefix + '__public'] = str(event)

        run_fields = {}
        if bid.speedrun:
            add_run_fields(run_fields, bid.speedrun, 'speedrun')
        parent_fields = {}
        if bid.parent:
            add_parent_fields(parent_fields, bid.parent, 'parent')
        event_fields = {}
        add_event_fields(event_fields, bid.event, 'event')

        return dict(
            fields=dict(
                public=str(bid),
                name=bid.name,
                canonical_url=(
                    request.build_absolute_uri(reverse('tracker:bid', args=(bid.id,)))
                ),
                description=bid.description,
                shortdescription=bid.shortdescription,
                event=bid.event_id,
                speedrun=bid.speedrun_id,
                total=str(bid.total),
                count=bid.count,
                goal=bid.goal,
                state=bid.state,
                istarget=bid.istarget,
                pinned=bid.pinned,
                revealedtime=format_time(bid.revealedtime),
                allowuseroptions=bid.allowuseroptions,
                biddependency=bid.biddependency_id,
                option_max_length=bid.option_max_length,
                parent=bid.parent_id,
                **run_fields,
                **parent_fields,
                **event_fields,
            ),
            model='tracker.bid',
            pk=bid.id,
        )

    def test_bid_with_parent(self):
        models.SpeedRun.objects.create(
            event=self.event,
            name='Test Run',
            run_time='5:00',
            setup_time='5:00',
            order=1,
        ).clean()
        parent = models.Bid.objects.create(
            name='Parent',
            allowuseroptions=True,
            speedrun=self.event.speedrun_set.first(),
            state='OPENED',
        )
        parent.clean()
        parent.save()
        child = models.Bid.objects.create(
            name='Child',
            allowuseroptions=False,
            parent=parent,
        )
        child.clean()
        child.save()
        request = self.factory.get(
            '/api/v1/search', dict(type='allbids', event=self.event.id)
        )
        request.user = self.anonymous_user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0], self.format_bid(parent, request))
        self.assertEqual(data[1], self.format_bid(child, request))


class TestDonor(APITestCase):
    model_name = 'donor'

    def setUp(self):
        super(TestDonor, self).setUp()
        self.add_user.user_permissions.add(
            Permission.objects.get(name='Can view full usernames')
        )

    @classmethod
    def format_donor(cls, donor, request):
        other_fields = {}

        if donor.visibility == 'FULL' or request.GET.get('donor_names', None) == '':
            other_fields['firstname'] = donor.firstname
            other_fields['lastname'] = donor.lastname
            other_fields['alias'] = donor.alias
            other_fields['alias_num'] = donor.alias_num
            other_fields['canonical_url'] = request.build_absolute_uri(
                donor.get_absolute_url()
            )
        elif donor.visibility == 'FIRST':
            other_fields['firstname'] = donor.firstname
            other_fields['lastname'] = f'{donor.lastname[0]}...'
            other_fields['alias'] = donor.alias
            other_fields['alias_num'] = donor.alias_num
            other_fields['canonical_url'] = request.build_absolute_uri(
                donor.get_absolute_url()
            )
        elif donor.visibility == 'ALIAS':
            other_fields['alias'] = donor.alias
            other_fields['alias_num'] = donor.alias_num
            other_fields['canonical_url'] = request.build_absolute_uri(
                donor.get_absolute_url()
            )

        return dict(
            fields=dict(
                public=donor.visible_name(),
                visibility=donor.visibility,
                **other_fields,
            ),
            model='tracker.donor',
            pk=donor.id,
        )

    def test_full_visibility_donor(self):
        donor = randgen.generate_donor(self.rand, visibility='FULL')
        donor.save()
        request = self.factory.get(reverse('tracker:api_v1:search'), dict(type='donor'))
        request.user = self.anonymous_user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0], self.format_donor(donor, request))

    def test_first_name_visibility_donor(self):
        donor = randgen.generate_donor(self.rand, visibility='FIRST')
        donor.save()
        request = self.factory.get(reverse('tracker:api_v1:search'), dict(type='donor'))
        request.user = self.anonymous_user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0], self.format_donor(donor, request))

    def test_alias_visibility_donor(self):
        donor = randgen.generate_donor(self.rand, visibility='ALIAS')
        donor.save()
        request = self.factory.get(reverse('tracker:api_v1:search'), dict(type='donor'))
        request.user = self.anonymous_user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0], self.format_donor(donor, request))

    def test_anonymous_visibility_donor(self):
        donor = randgen.generate_donor(self.rand, visibility='ANON')
        donor.save()
        request = self.factory.get(reverse('tracker:api_v1:search'), dict(type='donor'))
        request.user = self.anonymous_user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 0)

    def test_donor_full_names_without_permission(self):
        request = self.factory.get(
            reverse('tracker:api_v1:search'), dict(type='donor', donor_names='')
        )
        request.user = self.anonymous_user
        self.parseJSON(tracker.views.api.search(request), status_code=403)

    def test_donor_full_names_with_permission(self):
        donor = randgen.generate_donor(self.rand, visibility='ALIAS')
        donor.save()
        request = self.factory.get(
            reverse('tracker:api_v1:search'), dict(type='donor', donor_names='')
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0], self.format_donor(donor, request))


class TestDonation(APITestCase):
    model_name = 'donation'

    def setUp(self):
        super(TestDonation, self).setUp()
        self.add_user.user_permissions.add(
            Permission.objects.get(name='Can view all comments')
        )
        self.donor = randgen.generate_donor(self.rand, visibility='ANON')
        self.donor.save()

    @classmethod
    def format_donation(cls, donation, request):
        other_fields = {}

        donor = donation.donor

        if donor.visibility in ['FULL', 'FIRST', 'ALIAS']:
            other_fields['donor__alias'] = donor.alias
            other_fields['donor__alias_num'] = donor.alias_num
            other_fields['donor__canonical_url'] = request.build_absolute_uri(
                donor.get_absolute_url()
            )
            other_fields['donor__visibility'] = donor.visibility
            other_fields['donor'] = donor.pk

        # FIXME: this is super weird but maybe not worth fixing
        if 'all_comments' in request.GET:
            other_fields['donor__alias'] = donor.alias
            other_fields['donor__alias_num'] = donor.alias_num
            other_fields['donor__canonical_url'] = request.build_absolute_uri(
                donor.get_absolute_url()
            )
            other_fields['donor__visibility'] = donor.visibility
            other_fields['donor'] = donor.pk

        if donation.commentstate == 'APPROVED' or 'all_comments' in request.GET:
            other_fields['comment'] = donation.comment
            other_fields['commentlanguage'] = donation.commentlanguage

        return dict(
            fields=dict(
                amount=float(donation.amount),
                canonical_url=request.build_absolute_uri(donation.get_absolute_url()),
                commentstate=donation.commentstate,
                currency=donation.currency,
                domain=donation.domain,
                donor__public=donor.visible_name(),
                event=donation.event.pk,
                public=str(donation),
                readstate=donation.readstate,
                timereceived=format_time(donation.timereceived),
                transactionstate=donation.transactionstate,
                pinned=donation.pinned,
                **other_fields,
            ),
            model='tracker.donation',
            pk=donation.id,
        )

    def test_unapproved_comment(self):
        donation = randgen.generate_donation(
            self.rand, donor=self.donor, event=self.event, commentstate='PENDING'
        )
        donation.save()
        request = self.factory.get(
            reverse('tracker:api_v1:search'), dict(type='donation')
        )
        request.user = self.anonymous_user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 1)
        self.assertModelPresent(self.format_donation(donation, request), data)

    def test_unapproved_comment_with_permission(self):
        donation = randgen.generate_donation(
            self.rand, donor=self.donor, event=self.event, commentstate='PENDING'
        )
        donation.save()
        request = self.factory.get(
            reverse('tracker:api_v1:search'), dict(type='donation', all_comments='')
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 1)
        self.assertModelPresent(self.format_donation(donation, request), data)

    def test_unapproved_comment_without_permission(self):
        request = self.factory.get(
            reverse('tracker:api_v1:search'), dict(type='donation', all_comments='')
        )
        request.user = self.anonymous_user
        self.parseJSON(tracker.views.api.search(request), status_code=403)

    def test_approved_comment(self):
        donation = randgen.generate_donation(
            self.rand, donor=self.donor, event=self.event
        )
        donation.save()
        request = self.factory.get(
            reverse('tracker:api_v1:search'), dict(type='donation')
        )
        request.user = self.anonymous_user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 1)
        self.assertModelPresent(self.format_donation(donation, request), data)

    def test_donor_visibilities(self):
        donation = randgen.generate_donation(
            self.rand, donor=self.donor, event=self.event
        )
        donation.save()
        for visibility in ['FULL', 'FIRST', 'ALIAS', 'ANON']:
            self.donor.visibility = visibility
            self.donor.save()
            donation.donor.refresh_from_db()
            request = self.factory.get(
                reverse('tracker:api_v1:search'), dict(type='donation')
            )
            request.user = self.anonymous_user
            data = self.parseJSON(tracker.views.api.search(request))
            self.assertEqual(len(data), 1)
            self.assertModelPresent(
                self.format_donation(donation, request),
                data,
                msg=f'Visibility {visibility} gave an incorrect result',
            )

    def test_search_by_donor(self):
        donation = randgen.generate_donation(
            self.rand, donor=self.donor, event=self.event
        )
        donation.save()

        self.donor.alias = 'Foo'
        self.donor.visibility = 'ALIAS'
        self.donor.save()

        request = self.factory.get(
            reverse('tracker:api_v1:search'), dict(type='donation', donor=self.donor.id)
        )
        request.user = self.anonymous_user

        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 1)
        self.assertModelPresent(
            self.format_donation(donation, request),
            data,
            msg=f'Normal visibility gave an incorrect result',
        )

        self.donor.visibility = 'ANON'
        self.donor.save()

        request = self.factory.get(
            reverse('tracker:api_v1:search'), dict(type='donation', donor=self.donor.id)
        )
        request.user = self.anonymous_user

        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 0, msg='Anonymous donor was searchable')


class TestMilestone(APITestCase):
    model_name = 'milestone'

    @classmethod
    def format_milestone(cls, milestone, request):
        return dict(
            fields=dict(
                event=milestone.event_id,
                amount=float(milestone.amount),
                name=milestone.name,
                description=milestone.description,
                short_description=milestone.short_description,
                public=str(milestone),
                visible=milestone.visible,
            ),
            model='tracker.milestone',
            pk=milestone.pk,
        )

    def test_search(self):
        self.milestone = randgen.generate_milestone(self.rand, self.event)
        self.milestone.visible = True
        self.milestone.save()
        self.invisible_milestone = randgen.generate_milestone(self.rand, self.event)
        self.invisible_milestone.save()
        request = self.factory.get(
            reverse('tracker:api_v1:search'),
            dict(type='milestone', event=self.event.id),
        )
        request.user = self.anonymous_user

        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 1)
        self.assertModelPresent(
            self.format_milestone(self.milestone, request),
            data,
            msg=f'Milestone search gave an incorrect result',
        )
