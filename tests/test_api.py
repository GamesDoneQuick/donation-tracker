import tracker.models as models

from django.test import TransactionTestCase, RequestFactory
from django.contrib.auth.models import User, Permission
import tracker.views.api
import json
import pytz
import datetime

def format_time(dt):
    return dt.astimezone(pytz.utc).isoformat()[:-6] + 'Z'

class TestSpeedRun(TransactionTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(username='test')
        self.event1 = models.Event.objects.create(
            date=datetime.date.today(), targetamount=5, short='event1',
        )
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
        data = json.loads(tracker.views.api.search(request).content)
        self.assertEqual(len(data), 1)
        expected = self.format_run(self.run1)
        self.assertEqual(data[0], expected)

    def test_get_event_runs(self):
        request = self.factory.get('/api/v1/search', dict(type='run', event=self.run1.event_id))
        request.user = self.user
        data = json.loads(tracker.views.api.search(request).content)
        self.assertEqual(len(data), 4)
        self.assertIn(self.format_run(self.run1), data)
        self.assertIn(self.format_run(self.run2), data)
        self.assertIn(self.format_run(self.run3), data)
        self.assertIn(self.format_run(self.run4), data)

    def test_get_starttime_lte(self):
        request = self.factory.get('/api/v1/search', dict(type='run', starttime_lte=format_time(self.run2.starttime)))
        request.user = self.user
        data = json.loads(tracker.views.api.search(request).content)
        self.assertEqual(len(data), 2)
        self.assertIn(self.format_run(self.run1), data)
        self.assertIn(self.format_run(self.run2), data)

    def test_get_starttime_gte(self):
        request = self.factory.get('/api/v1/search', dict(type='run', starttime_gte=format_time(self.run2.starttime)))
        request.user = self.user
        data = json.loads(tracker.views.api.search(request).content)
        self.assertEqual(len(data), 3)
        self.assertIn(self.format_run(self.run2), data)
        self.assertIn(self.format_run(self.run4), data)
        self.assertIn(self.format_run(self.run5), data)

    def test_get_endtime_lte(self):
        request = self.factory.get('/api/v1/search', dict(type='run', endtime_lte=format_time(self.run2.endtime)))
        request.user = self.user
        data = json.loads(tracker.views.api.search(request).content)
        self.assertEqual(len(data), 2)
        self.assertIn(self.format_run(self.run1), data)
        self.assertIn(self.format_run(self.run2), data)

    def test_get_endtime_gte(self):
        request = self.factory.get('/api/v1/search', dict(type='run', endtime_gte=format_time(self.run2.endtime)))
        request.user = self.user
        data = json.loads(tracker.views.api.search(request).content)
        self.assertEqual(len(data), 3)
        self.assertIn(self.format_run(self.run2), data)
        self.assertIn(self.format_run(self.run4), data)
        self.assertIn(self.format_run(self.run5), data)

    def test_tech_notes(self):
        request = self.factory.get('/api/v1/search', dict(type='run', id=self.run1.id))
        request.user = self.user
        self.user.user_permissions.add(Permission.objects.get(name='Can view tech notes'))
        data = json.loads(tracker.views.api.search(request).content)
        expected = self.format_run(self.run1)
        expected['fields']['tech_notes'] = self.run1.tech_notes
        self.assertEqual(data[0], expected)
