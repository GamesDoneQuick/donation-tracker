import tracker.models as models

from django.test import TestCase, TransactionTestCase

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
            name='Test Run 3', run_time='0:20:00', setup_time='0:05:00', order=None)
        self.run4 = models.SpeedRun.objects.create(
            name='Test Run 4', run_time='0', setup_time='0', order=3)
        self.runner1 = models.Runner.objects.create(name='trihex')

    def test_first_run_start_time(self):
        self.assertEqual(self.run1.starttime, self.event1.timezone.localize(
            datetime.datetime.combine(self.event1.date, datetime.time(11,30))))

    def test_second_run_start_time(self):
        self.assertEqual(self.run2.starttime, datetime.datetime.combine(
            self.event1.date, datetime.time(12, 50, tzinfo=self.event1.timezone)))

    def test_null_order_run_start_time(self):
        self.assertEqual(self.run3.starttime, None)

    def test_null_order_run_end_time(self):
        self.assertEqual(self.run3.endtime, None)

    def test_no_run_time_run_start_time(self):
        self.assertEqual(self.run4.starttime, None)

    def test_no_run_time_run_end_time(self):
        self.assertEqual(self.run4.endtime, None)

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
