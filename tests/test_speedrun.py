import datetime
import itertools

import copy
import pytz
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import TransactionTestCase, RequestFactory
from django.urls import reverse

from tracker import models, signals
from .util import today_noon, ChangeSignalsTestMixin


class TestSpeedRun(TransactionTestCase, ChangeSignalsTestMixin):
    def setUp(self):
        self.event1 = models.Event.objects.create(datetime=today_noon, targetamount=5)
        self.run1 = models.SpeedRun.objects.create(
            name='Test Run', run_time='0:45:00', setup_time='0:05:00', order=1
        )
        self.run2 = models.SpeedRun.objects.create(
            name='Test Run 2', run_time='0:15:00', setup_time='0:05:00', order=2
        )
        self.run3 = models.SpeedRun.objects.create(
            name='Test Run 3', run_time='0:05:00', order=3
        )
        self.run4 = models.SpeedRun.objects.create(
            name='Test Run 4', run_time='0:20:00', setup_time='0:05:00', order=None
        )
        # removing a run should compress any holes
        self.run5 = models.SpeedRun.objects.create(name='Test Run 5', order=5)
        self.runner1 = models.Runner.objects.create(name='trihex')
        self.runner2 = models.Runner.objects.create(name='neskamikaze')

    def test_first_run_start_time(self):
        self.assertEqual(self.run1.starttime, self.event1.datetime)

    def test_second_run_start_time(self):
        self.assertEqual(
            self.run2.starttime, self.run1.starttime + datetime.timedelta(minutes=50)
        )

    def test_no_setup_time_run_start_time(self):
        self.assertEqual(
            self.run3.starttime, self.run2.starttime + datetime.timedelta(minutes=20)
        )

    def test_no_setup_time_run_end_time(self):
        self.assertEqual(
            self.run3.endtime, self.run3.starttime + datetime.timedelta(minutes=5)
        )

    def test_null_order_run_start_time(self):
        self.assertEqual(self.run4.starttime, None)

    def test_null_order_run_end_time(self):
        self.assertEqual(self.run4.endtime, None)

    def test_removing_run_from_schedule(self):
        self.run1.order = None
        self.run1.save()
        self.run2.refresh_from_db()
        self.assertEqual(self.run2.starttime, self.event1.datetime)

    def test_update_runners_on_save(self):
        self.run1.runners.add(self.runner1, self.runner2)
        self.run1.deprecated_runners = ''
        self.run1.save()
        self.assertEqual(
            self.run1.deprecated_runners,
            ', '.join(sorted([self.runner2.name, self.runner1.name])),
        )

    def test_update_runners_on_m2m(self):
        self.run1.runners.add(self.runner1, self.runner2)
        self.run1.refresh_from_db()
        self.assertEqual(
            self.run1.deprecated_runners,
            ', '.join(sorted([self.runner1.name, self.runner2.name])),
        )
        self.run1.runners.remove(self.runner1)
        self.run1.refresh_from_db()
        self.assertEqual(
            self.run1.deprecated_runners, ', '.join(sorted([self.runner2.name]))
        )

    def test_signal_run_time_change(self):
        old_run = copy.copy(self.run1)
        delta = datetime.timedelta(minutes=5)
        self.run1.run_time += delta
        results = signals.model_changed.send(
            sender=self.run1.__class__, instance=(old_run, self.run1),
        )
        expected_runs = [self.run2, self.run3]

        delta = datetime.timedelta(minutes=5)

        self.assertExpectedResultsPresent(
            {
                'changes': [
                    (
                        run,
                        [
                            ('starttime', (run.starttime, run.starttime + delta)),
                            ('endtime', (run.endtime, run.endtime + delta)),
                        ],
                    )
                    for run in expected_runs
                ]
            },
            results,
        )

        for callback in itertools.chain.from_iterable(
            result[1].get('callbacks', []) for result in results
        ):
            callback()

        for run in expected_runs:
            changed_run = models.SpeedRun.objects.get(id=run.id)
            self.assertEqual(run.starttime + delta, changed_run.starttime)
            self.assertEqual(run.endtime + delta, changed_run.endtime)

    def test_signal_order_nullify(self):
        old_run = copy.copy(self.run2)
        self.run2.order = None
        self.run2.save(fix_time=False, fix_runners=False)
        results = signals.model_changed.send(
            sender=self.run1.__class__, instance=(old_run, self.run2),
        )

        delta = datetime.timedelta(minutes=20)

        self.assertExpectedResultsPresent(
            {
                'changes': [
                    (
                        self.run3,
                        [
                            ('order', (self.run3.order, old_run.order)),
                            (
                                'starttime',
                                (self.run3.starttime, self.run3.starttime - delta),
                            ),
                            ('endtime', (self.run3.endtime, self.run3.endtime - delta)),
                        ],
                    ),
                    (self.run5, [('order', (self.run5.order, old_run.order + 1))]),
                ]
            },
            results,
        )

        old_start = self.run3.starttime

        for callback in itertools.chain.from_iterable(
            result[1].get('callbacks', []) for result in results
        ):
            callback()

        self.run3.refresh_from_db()
        self.run5.refresh_from_db()
        self.assertEqual(self.run3.order, old_run.order)
        self.assertEqual(self.run3.starttime, old_start - delta)
        self.assertEqual(self.run5.order, old_run.order + 1)


class TestMoveSpeedRun(TransactionTestCase):
    def setUp(self):
        self.event1 = models.Event.objects.create(datetime=today_noon, targetamount=5)
        self.run1 = models.SpeedRun.objects.create(
            name='Test Run 1', run_time='0:45:00', setup_time='0:05:00', order=1
        )
        self.run2 = models.SpeedRun.objects.create(
            name='Test Run 2', run_time='0:15:00', setup_time='0:05:00', order=2
        )
        self.run3 = models.SpeedRun.objects.create(
            name='Test Run 3', run_time='0:20:00', setup_time='0:05:00', order=3
        )
        self.run4 = models.SpeedRun.objects.create(
            name='Test Run 4', run_time='0:20:00', setup_time='0:05:00', order=None
        )

    def test_after_to_before(self):
        from tracker.views.commands import MoveSpeedRun

        output, status = MoveSpeedRun(
            {'moving': self.run2.id, 'other': self.run1.id, 'before': True}
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(output), 2)
        self.run1.refresh_from_db()
        self.run2.refresh_from_db()
        self.run3.refresh_from_db()
        self.assertEqual(self.run1.order, 2)
        self.assertEqual(self.run2.order, 1)
        self.assertEqual(self.run3.order, 3)

    def test_after_to_after(self):
        from tracker.views.commands import MoveSpeedRun

        output, status = MoveSpeedRun(
            {'moving': self.run3.id, 'other': self.run1.id, 'before': False}
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(output), 2)
        self.run1.refresh_from_db()
        self.run2.refresh_from_db()
        self.run3.refresh_from_db()
        self.assertEqual(self.run1.order, 1)
        self.assertEqual(self.run2.order, 3)
        self.assertEqual(self.run3.order, 2)

    def test_before_to_before(self):
        from tracker.views.commands import MoveSpeedRun

        output, status = MoveSpeedRun(
            {'moving': self.run1.id, 'other': self.run3.id, 'before': True}
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(output), 2)
        self.run1.refresh_from_db()
        self.run2.refresh_from_db()
        self.run3.refresh_from_db()
        self.assertEqual(self.run1.order, 2)
        self.assertEqual(self.run2.order, 1)
        self.assertEqual(self.run3.order, 3)

    def test_before_to_after(self):
        from tracker.views.commands import MoveSpeedRun

        output, status = MoveSpeedRun(
            {'moving': self.run1.id, 'other': self.run2.id, 'before': False}
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(output), 2)
        self.run1.refresh_from_db()
        self.run2.refresh_from_db()
        self.run3.refresh_from_db()
        self.assertEqual(self.run1.order, 2)
        self.assertEqual(self.run2.order, 1)
        self.assertEqual(self.run3.order, 3)

    def test_unordered_to_before(self):
        from tracker.views.commands import MoveSpeedRun

        output, status = MoveSpeedRun(
            {'moving': self.run4.id, 'other': self.run2.id, 'before': True}
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(output), 3)
        self.run2.refresh_from_db()
        self.run3.refresh_from_db()
        self.run4.refresh_from_db()
        self.assertEqual(self.run2.order, 3)
        self.assertEqual(self.run3.order, 4)
        self.assertEqual(self.run4.order, 2)

    def test_unordered_to_after(self):
        from tracker.views.commands import MoveSpeedRun

        output, status = MoveSpeedRun(
            {'moving': self.run4.id, 'other': self.run2.id, 'before': False}
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(output), 2)
        self.run2.refresh_from_db()
        self.run3.refresh_from_db()
        self.run4.refresh_from_db()
        self.assertEqual(self.run2.order, 2)
        self.assertEqual(self.run3.order, 4)
        self.assertEqual(self.run4.order, 3)


class TestSpeedRunAdmin(TransactionTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.sessions = SessionMiddleware()
        self.messages = MessageMiddleware()
        self.event1 = models.Event.objects.create(
            datetime=today_noon,
            targetamount=5,
            timezone=pytz.timezone(getattr(settings, 'TIME_ZONE', 'America/Denver')),
        )
        self.run1 = models.SpeedRun.objects.create(
            name='Test Run 1', run_time='0:45:00', setup_time='0:05:00', order=1
        )
        self.run2 = models.SpeedRun.objects.create(
            name='Test Run 2', run_time='0:15:00', setup_time='0:05:00', order=2
        )
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'nobody@example.com', 'password')

    def test_not_logged_in_redirects_without_change(self):
        resp = self.client.post(
            reverse('admin:start_run', args=(self.run2.id,)),
            data={
                'run_time': '0:41:20',
                'start_time': '%s 12:51:00' % self.event1.date,
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.run1.refresh_from_db()
        self.assertEqual(self.run1.run_time, '0:45:00')
        self.assertEqual(self.run1.setup_time, '0:05:00')

    def test_start_run(self):
        self.client.login(username='admin', password='password')
        resp = self.client.post(
            reverse('admin:start_run', args=(self.run2.id,)),
            data={
                'run_time': '0:41:20',
                'start_time': '%s 12:51:00' % self.event1.date,
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.run1.refresh_from_db()
        self.assertEqual(self.run1.run_time, '0:41:20')
        self.assertEqual(self.run1.setup_time, '0:09:40')

    def test_invalid_time(self):
        self.client.login(username='admin', password='password')
        resp = self.client.post(
            reverse('admin:start_run', args=(self.run2.id,)),
            data={
                'run_time': '0:41:20',
                'start_time': '%s 11:21:00' % self.event1.date,
            },
        )
        self.assertEqual(resp.status_code, 400)
