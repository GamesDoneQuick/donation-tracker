from django.contrib.auth.models import User
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware

import tracker.models as models

from django.test import TransactionTestCase, RequestFactory

import datetime

class TestSpeedRun(TransactionTestCase):

    def setUp(self):
        self.event1 = models.Event.objects.create(
            date=datetime.date.today(), targetamount=5)
        self.run1 = models.SpeedRun.objects.create(
            name='Test Run', run_time='0:45:00', setup_time='0:05:00', order=1)
        self.run2 = models.SpeedRun.objects.create(
            name='Test Run 2', run_time='0:15:00', setup_time='0:05:00', order=2)
        self.run3 = models.SpeedRun.objects.create(
            name='Test Run 3', run_time='0:05:00', order=3)
        self.run4 = models.SpeedRun.objects.create(
            name='Test Run 4', run_time='0:20:00', setup_time='0:05:00', order=None)
        self.run5 = models.SpeedRun.objects.create(
            name='Test Run 5', order=4)
        self.runner1 = models.Runner.objects.create(name='trihex')
        self.runner2 = models.Runner.objects.create(name='neskamikaze')

    def test_first_run_start_time(self):
        self.assertEqual(self.run1.starttime, self.event1.timezone.localize(
            datetime.datetime.combine(self.event1.date, datetime.time(11, 30))))

    def test_second_run_start_time(self):
        self.assertEqual(self.run2.starttime, self.run1.starttime + datetime.timedelta(minutes=50))

    def test_no_setup_time_run_start_time(self):
        self.assertEqual(self.run3.starttime, self.run2.starttime + datetime.timedelta(minutes=20))

    def test_no_setup_time_run_end_time(self):
        self.assertEqual(self.run3.endtime, self.run2.endtime + datetime.timedelta(minutes=5))

    def test_null_order_run_start_time(self):
        self.assertEqual(self.run4.starttime, None)

    def test_null_order_run_end_time(self):
        self.assertEqual(self.run4.endtime, None)

    def test_no_run_or_setup_time_run_start_time(self):
        self.assertEqual(self.run5.starttime, None)

    def test_no_run_or_setup_time_run_end_time(self):
        self.assertEqual(self.run5.endtime, None)

    def test_removing_run_from_schedule(self):
        self.run1.order = None
        self.run1.save()
        self.run2.refresh_from_db()
        self.assertEqual(self.run2.starttime, self.event1.timezone.localize(
            datetime.datetime.combine(self.event1.date, datetime.time(11,30))))

    def test_fix_runners_with_valid_runners(self):
        self.run1.deprecated_runners = 'trihex'
        self.run1.save()
        self.run1.refresh_from_db()
        self.assertIn(self.runner1, self.run1.runners.all())
        self.assertEqual(self.run1.deprecated_runners, 'trihex')

    def test_fix_runners_with_invalid_runners(self):
        self.run1.deprecated_runners = 'trihex, dugongue'
        self.run1.save()
        self.run1.refresh_from_db()
        self.assertNotIn(self.runner1, self.run1.runners.all())
        self.assertEqual(self.run1.deprecated_runners, 'trihex, dugongue')

    def test_fix_runners_when_runners_are_set(self):
        self.run1.deprecated_runners = 'trihex, dugongue'
        self.run1.runners.add(self.runner1)
        self.run1.save()
        self.run1.refresh_from_db()
        self.assertEqual(self.run1.deprecated_runners, 'trihex')

    def test_fix_runners_when_runners_are_set_with_new_valid_runners(self):
        return # pending
        self.run1.deprecated_runners = 'trihex, neskamikaze'
        self.run1.runners.add(self.runner1)
        self.run1.save()
        self.run1.refresh_from_db()
        self.assertIn(self.runner1, self.run1.runners.all())
        self.assertIn(self.runner2, self.run1.runners.all())
        self.assertEqual(self.run1.deprecated_runners, 'trihex, neskamikaze')


class TestMoveSpeedRun(TransactionTestCase):

    def setUp(self):
        self.event1 = models.Event.objects.create(
            date=datetime.date.today(), targetamount=5)
        self.run1 = models.SpeedRun.objects.create(
            name='Test Run 1', run_time='0:45:00', setup_time='0:05:00', order=1)
        self.run2 = models.SpeedRun.objects.create(
            name='Test Run 2', run_time='0:15:00', setup_time='0:05:00', order=2)
        self.run3 = models.SpeedRun.objects.create(
            name='Test Run 3', run_time='0:20:00', setup_time='0:05:00', order=3)
        self.run4 = models.SpeedRun.objects.create(
            name='Test Run 4', run_time='0:20:00', setup_time='0:05:00', order=None)

    def test_after_to_before(self):
        from tracker.views.commands import MoveSpeedRun
        output, status = MoveSpeedRun(
            {'moving': self.run2.id, 'other': self.run1.id, 'before': True})
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
            {'moving': self.run3.id, 'other': self.run1.id, 'before': False})
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
            {'moving': self.run1.id, 'other': self.run3.id, 'before': True})
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
            {'moving': self.run1.id, 'other': self.run2.id, 'before': False})
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
            {'moving': self.run4.id, 'other': self.run2.id, 'before': True})
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
            {'moving': self.run4.id, 'other': self.run2.id, 'before': False})
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
            date=datetime.date.today(), targetamount=5)
        self.run1 = models.SpeedRun.objects.create(
            name='Test Run 1', run_time='0:45:00', setup_time='0:05:00', order=1)
        self.run2 = models.SpeedRun.objects.create(
            name='Test Run 2', run_time='0:15:00', setup_time='0:05:00', order=2)
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'nobody@example.com', 'password')

    def test_not_logged_in(self):
        resp = self.client.post('/admin/start_run/%s' % self.run2.id, data={'run_time': '0:41:20', 'start_time': '%s 12:21:00' % self.event1.date})
        self.assertEqual(resp.status_code, 403)

    def test_start_run(self):
        self.client.login(username='admin', password='password')
        resp = self.client.post('/admin/start_run/%s' % self.run2.id, data={'run_time': '0:41:20', 'start_time': '%s 12:21:00' % self.event1.date})
        self.assertEqual(resp.status_code, 302)
        self.run1.refresh_from_db()
        self.assertEqual(self.run1.run_time, '0:41:20')
        self.assertEqual(self.run1.setup_time, '0:09:40')

    def test_invalid_time(self):
        self.client.login(username='admin', password='password')
        resp = self.client.post('/admin/start_run/%s' % self.run2.id, data={'run_time': '0:41:20', 'start_time': '%s 11:21:00' % self.event1.date})
        self.assertEqual(resp.status_code, 400)