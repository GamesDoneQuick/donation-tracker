import tracker.models as models

from django.test import TransactionTestCase, RequestFactory
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry, ADDITION as LogEntryADDITION, CHANGE as LogEntryCHANGE, DELETION as LogEntryDELETION
import tracker.views.api
import json
import pytz
import datetime


def format_time(dt):
    return dt.astimezone(pytz.utc).isoformat()[:-6] + 'Z'


class APITestCase(TransactionTestCase):
    model_name = None

    def parseJSON(self, response, status_code=200):
        self.assertEqual(response.status_code, status_code, msg='Status code is not %d\n"""%s"""' % (status_code, response.content))
        try:
            return json.loads(response.content)
        except Exception as e:
            raise AssertionError('Could not parse json: %s\n"""%s"""' % (e, response.content))

    def assertModelPresent(self, expected_model, data):
        found_model = None
        for model in data:
            if model['pk'] == expected_model['pk'] and model['model'] == expected_model['model']:
                found_model = model
                break
        if not found_model:
            raise AssertionError('Could not find model "%s:%s" in data' % (expected_model['model'], expected_model['pk']))
        extra_keys = set(found_model['fields'].keys()) - set(expected_model['fields'].keys())
        missing_keys = set(expected_model['fields'].keys()) - set(found_model['fields'].keys())
        unequal_keys = [
            k for k in expected_model['fields'].keys()
                if k in found_model['fields'] and found_model['fields'][k] != expected_model['fields'][k]
        ]
        problems = [u'Extra key: "%s"' % k for k in extra_keys] + \
                   [u'Missing key: "%s"' % k for k in missing_keys] + \
                   [u'Value for key "%s" unequal: %r != %r' % (k, expected_model['fields'][k], found_model['fields'][k]) for k in unequal_keys]
        if problems:
            raise AssertionError('Model "%s:%s" was incorrect:\n%s' % (expected_model['model'], expected_model['pk'], '\n'.join(problems)))

    def assertModelNotPresent(self, unexpected_model, data):
        found_model = None
        for model in data:
            if model['pk'] == unexpected_model['pk'] and model['model'] == unexpected_model['model']:
                found_model = model
                break
        if not found_model:
            raise AssertionError('Found model "%s:%s" in data' % (unexpected_model['model'], unexpected_model['pk']))

    def setUp(self):
        self.factory = RequestFactory()
        self.locked_event = models.Event.objects.create(
            date=datetime.date.today() - datetime.timedelta(days=180), targetamount=5, short='locked', name='Locked Event'
        )
        self.event = models.Event.objects.create(
            date=datetime.date.today(), targetamount=5, short='event', name='Test Event'
        )
        self.user = User.objects.create(username='test')
        self.add_user = User.objects.create(username='add')
        self.locked_user = User.objects.create(username='locked')
        self.locked_user.user_permissions.add(Permission.objects.get(name='Can edit locked events'))
        if self.model_name:
            self.add_user.user_permissions.add(Permission.objects.get(name='Can add %s' % self.model_name),
                                               Permission.objects.get(name='Can change %s' % self.model_name))
            self.locked_user.user_permissions.add(Permission.objects.get(name='Can add %s' % self.model_name),
                                                  Permission.objects.get(name='Can change %s' % self.model_name))
        self.super_user = User.objects.create(username='super', is_superuser=True)


class TestGeneric(APITestCase):
    """generic cases that could apply to any class, even if they use a specific one for testing purposes"""
    def test_add_with_bad_type(self):
        request = self.factory.post('/api/v1/add', dict(type='nonsense'))
        request.user = self.super_user
        data = self.parseJSON(tracker.views.api.add(request), status_code=400)
        self.assertEqual('Malformed Add Parameters', data['error'])

    def test_add_with_bad_field(self):
        request = self.factory.post('/api/v1/add', dict(type='run', nonsense='nonsense'))
        request.user = self.super_user
        data = self.parseJSON(tracker.views.api.add(request), status_code=400)
        self.assertEqual('Field does not exist', data['error'])

    def test_add_log(self):
        request = self.factory.post('/api/v1/add', dict(type='runner', name='trihex', stream='https://twitch.tv/trihex'))
        request.user = self.super_user
        data = self.parseJSON(tracker.views.api.add(request))
        runner = models.Runner.objects.get(pk=data[0]['pk'])
        add_entry = LogEntry.objects.order_by('-pk')[1]
        self.assertEqual(int(add_entry.object_id), runner.id)
        self.assertEqual(add_entry.content_type, ContentType.objects.get_for_model(models.Runner))
        self.assertEqual(add_entry.action_flag, LogEntryADDITION)
        change_entry = LogEntry.objects.order_by('-pk')[0]
        self.assertEqual(int(change_entry.object_id), runner.id)
        self.assertEqual(change_entry.content_type, ContentType.objects.get_for_model(models.Runner))
        self.assertEqual(change_entry.action_flag, LogEntryCHANGE)
        self.assertIn(u'Set name to "%s".' % runner.name, change_entry.change_message)
        self.assertIn(u'Set stream to "%s".' % runner.stream, change_entry.change_message)

    def test_change_log(self):
        old_runner = models.Runner.objects.create(name='PJ', youtube='TheSuperSNES')
        request = self.factory.post('/api/v1/edit', dict(type='runner', id=old_runner.id, name='trihex', stream='https://twitch.tv/trihex', youtube=''))
        request.user = self.super_user
        data = self.parseJSON(tracker.views.api.edit(request))
        runner = models.Runner.objects.get(pk=data[0]['pk'])
        entry = LogEntry.objects.order_by('pk').last()
        self.assertEqual(int(entry.object_id), runner.id)
        self.assertEqual(entry.content_type, ContentType.objects.get_for_model(models.Runner))
        self.assertEqual(entry.action_flag, LogEntryCHANGE)
        self.assertIn(u'Changed name from "%s" to "%s".' % (old_runner.name, runner.name), entry.change_message)
        self.assertIn(u'Changed stream from empty to "%s".' % runner.stream, entry.change_message)
        self.assertIn(u'Changed youtube from "%s" to empty.' % old_runner.youtube, entry.change_message)

    def test_change_log_m2m(self):
        run = models.SpeedRun.objects.create(name='Test Run', run_time='0:15:00')
        runner1 = models.Runner.objects.create(name='PJ')
        runner2 = models.Runner.objects.create(name='trihex')
        request = self.factory.post('/api/v1/edit', dict(type='run', id=run.id, runners='%s,%s' % (runner1.name, runner2.name)))
        request.user = self.super_user
        self.parseJSON(tracker.views.api.edit(request))
        entry = LogEntry.objects.order_by('pk').last()
        self.assertEqual(int(entry.object_id), run.id)
        self.assertEqual(entry.content_type, ContentType.objects.get_for_model(models.SpeedRun))
        self.assertEqual(entry.action_flag, LogEntryCHANGE)
        self.assertIn(u'Changed runners from empty to "%s".' % ([unicode(runner1), unicode(runner2)],), entry.change_message)

    def test_delete_log(self):
        old_runner = models.Runner.objects.create(name='PJ', youtube='TheSuperSNES')
        request = self.factory.post('/api/v1/delete', dict(type='runner', id=old_runner.id))
        request.user = self.super_user
        self.parseJSON(tracker.views.api.delete(request))
        self.assertFalse(models.Runner.objects.filter(pk=old_runner.pk).exists())
        entry = LogEntry.objects.order_by('pk').last()
        self.assertEqual(int(entry.object_id), old_runner.id)
        self.assertEqual(entry.content_type, ContentType.objects.get_for_model(models.Runner))
        self.assertEqual(entry.action_flag, LogEntryDELETION)


class TestSpeedRun(APITestCase):
    model_name = 'Speed Run'

    def setUp(self):
        super(TestSpeedRun, self).setUp()
        self.run1 = models.SpeedRun.objects.create(
            name='Test Run',
            category='test%',
            giantbomb_id=0xdeadbeef,
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
            date=datetime.date.today() + datetime.timedelta(days=1), targetamount=5, short='event2',
        )
        self.run5 = models.SpeedRun.objects.create(
            name='Test Run 5', run_time='0:05:00', setup_time='0', order=1, event=self.event2
        )

    @classmethod
    def format_run(cls, run):
        return dict(
            fields=dict(
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
                public=unicode(run),
                release_year=run.release_year,
                run_time=run.run_time,
                runners=[runner.id for runner in run.runners.all()],
                setup_time=run.setup_time,
                starttime=format_time(run.starttime) if run.starttime else run.starttime,
            ),
            model=u'tracker.speedrun',
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
        request = self.factory.get('/api/v1/search', dict(type='run', event=self.run1.event_id))
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 4)
        self.assertModelPresent(self.format_run(self.run1), data)
        self.assertModelPresent(self.format_run(self.run2), data)
        self.assertModelPresent(self.format_run(self.run3), data)
        self.assertModelPresent(self.format_run(self.run4), data)

    def test_get_starttime_lte(self):
        request = self.factory.get('/api/v1/search', dict(type='run', starttime_lte=format_time(self.run2.starttime)))
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 2)
        self.assertModelPresent(self.format_run(self.run1), data)
        self.assertModelPresent(self.format_run(self.run2), data)

    def test_get_starttime_gte(self):
        request = self.factory.get('/api/v1/search', dict(type='run', starttime_gte=format_time(self.run2.starttime)))
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 3)
        self.assertModelPresent(self.format_run(self.run2), data)
        self.assertModelPresent(self.format_run(self.run4), data)
        self.assertModelPresent(self.format_run(self.run5), data)

    def test_get_endtime_lte(self):
        request = self.factory.get('/api/v1/search', dict(type='run', endtime_lte=format_time(self.run2.endtime)))
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 2)
        self.assertModelPresent(self.format_run(self.run1), data)
        self.assertModelPresent(self.format_run(self.run2), data)

    def test_get_endtime_gte(self):
        request = self.factory.get('/api/v1/search', dict(type='run', endtime_gte=format_time(self.run2.endtime)))
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 3)
        self.assertModelPresent(self.format_run(self.run2), data)
        self.assertModelPresent(self.format_run(self.run4), data)
        self.assertModelPresent(self.format_run(self.run5), data)

    def test_add_with_category(self):
        request = self.factory.post('/api/v1/add', dict(type='run', name='Added Run With Category', run_time='0:15:00', setup_time='0:05:00', category='100%'))
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.add(request))
        self.assertEqual(len(data), 1)
        self.assertEqual(models.SpeedRun.objects.get(pk=data[0]['pk']).category, '100%')

    def test_edit_with_category(self):
        request = self.factory.post('/api/v1/edit', dict(type='run', id=self.run2.id, category='100%'))
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.edit(request))
        self.assertEqual(len(data), 1)
        self.assertEqual(models.SpeedRun.objects.get(pk=data[0]['pk']).category, '100%')

    def test_edit_with_runners_as_ids(self):
        request = self.factory.post('/api/v1/edit', dict(type='run', id=self.run2.id, runners='%d,%d' % (self.runner1.id, self.runner2.id)))
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.edit(request))
        self.assertEqual(len(data), 1)
        self.assertItemsEqual(models.SpeedRun.objects.get(pk=data[0]['pk']).runners.all(), [self.runner1, self.runner2])

    def test_edit_with_runners_as_json_ids(self):
        request = self.factory.post('/api/v1/edit', dict(type='run', id=self.run2.id, runners=json.dumps([self.runner1.id, self.runner2.id])))
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.edit(request))
        self.assertEqual(len(data), 1)
        self.assertItemsEqual(models.SpeedRun.objects.get(pk=data[0]['pk']).runners.all(), [self.runner1, self.runner2])

    def test_edit_with_runners_as_ids_invalid(self):
        request = self.factory.post('/api/v1/edit', dict(type='run', id=self.run2.id, runners='%d,%d' % (self.runner1.id, 6666)))
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.edit(request), status_code=400)
        self.assertEqual('Foreign Key relation could not be found', data['error'])

    def test_edit_with_runners_as_names(self):
        request = self.factory.post('/api/v1/edit', dict(type='run', id=self.run2.id, runners='%s,%s' % (self.runner1.name, self.runner2.name)))
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.edit(request))
        self.assertEqual(len(data), 1)
        self.assertItemsEqual(models.SpeedRun.objects.get(pk=data[0]['pk']).runners.all(), [self.runner1, self.runner2])

    def test_edit_with_runners_as_json_names(self):
        request = self.factory.post('/api/v1/edit', dict(type='run', id=self.run2.id, runners=json.dumps([self.runner1.name, self.runner2.name])))
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.edit(request))
        self.assertEqual(len(data), 1)
        self.assertItemsEqual(models.SpeedRun.objects.get(pk=data[0]['pk']).runners.all(), [self.runner1, self.runner2])

    def test_edit_with_runners_as_json_natural_keys(self):
        request = self.factory.post('/api/v1/edit', dict(type='run', id=self.run2.id, runners=json.dumps([self.runner1.natural_key(), self.runner2.natural_key()])))
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.edit(request))
        self.assertEqual(len(data), 1)
        self.assertItemsEqual(models.SpeedRun.objects.get(pk=data[0]['pk']).runners.all(), [self.runner1, self.runner2])

    def test_edit_with_runners_as_names_invalid(self):
        request = self.factory.post('/api/v1/edit', dict(type='run', id=self.run2.id, runners='%s,%s' % (self.runner1.name, 'nonsense')))
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.edit(request), status_code=400)
        self.assertEqual('Foreign Key relation could not be found', data['error'])

    def test_tech_notes(self):
        request = self.factory.get('/api/v1/search', dict(type='run', id=self.run1.id))
        request.user = self.user
        self.user.user_permissions.add(Permission.objects.get(name='Can view tech notes'))
        data = self.parseJSON(tracker.views.api.search(request))
        expected = self.format_run(self.run1)
        expected['fields']['tech_notes'] = self.run1.tech_notes
        self.assertEqual(data[0], expected)


class TestPrize(APITestCase):
    model_name = 'prize'

    def setUp(self):
        super(TestPrize, self).setUp()

    def test_add_with_new_category(self):
        self.add_user.user_permissions.add(Permission.objects.get(name='Can add Prize Category'))
        request = self.factory.post('/api/v1/add',
                                    dict(type='prize',
                                         name='Added Prize With Category',
                                         event=json.dumps(self.event.natural_key()),
                                         handler=json.dumps(self.add_user.natural_key()),
                                         category='Grand'))
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.add(request))
        self.assertEqual(len(data), 1)
        self.assertEqual(models.Prize.objects.get(pk=data[0]['pk']).category, models.PrizeCategory.objects.get(name='Grand'))

    def test_add_with_new_category_without_category_add_permission(self):
        request = self.factory.post('/api/v1/add',
                                    dict(type='prize',
                                         name='Added Prize With Category',
                                         event=json.dumps(self.event.natural_key()),
                                         handler=json.dumps(self.add_user.natural_key()),
                                         category='Grand'))
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.add(request), status_code=400)
        self.assertEqual('Foreign Key relation could not be found', data['error'])
