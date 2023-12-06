import datetime
import random
from unittest import skipIf

import django
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TransactionTestCase
from django.urls import reverse

import tracker.models as models
from tracker import settings

from . import randgen
from .util import today_noon

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo


class TestSpeedRun(TransactionTestCase):
    def setUp(self):
        self.event1 = models.Event.objects.create(datetime=today_noon, targetamount=5)
        self.run1 = models.SpeedRun.objects.create(
            name='Test Run', run_time='45:00', setup_time='5:00', order=1
        )
        self.run2 = models.SpeedRun.objects.create(
            name='Test Run 2', run_time='15:00', setup_time='5:00', order=2
        )
        self.run3 = models.SpeedRun.objects.create(
            name='Test Run 3', run_time='5:00', order=3
        )
        self.run4 = models.SpeedRun.objects.create(
            name='Test Run 4', run_time='1:20:00', setup_time='5:00', order=None
        )
        self.run5 = models.SpeedRun.objects.create(name='Test Run 5', order=4)
        self.runner1 = models.Runner.objects.create(name='trihex')
        self.runner2 = models.Runner.objects.create(name='neskamikaze')

    # TODO: maybe disallow partial seconds? this cropped as a bug but we never actually use milliseconds

    def test_run_time(self):
        self.run1.run_time = '45:00.1'
        self.run1.save()
        self.run1.refresh_from_db()
        self.assertEqual(self.run1.run_time, '0:45:00.100')

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
            self.run3.endtime, self.run2.endtime + datetime.timedelta(minutes=5)
        )

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

    def test_anchor_time(self):
        self.run3.anchor_time = self.run3.starttime
        self.run3.save()
        self.run1.clean()
        with self.subTest('run time drift'), self.assertRaises(ValidationError):
            self.run1.run_time = '1:00:00'
            self.run1.clean()
        self.run1.refresh_from_db()
        with self.subTest('setup time drift'), self.assertRaises(ValidationError):
            self.run1.run_time = '45:00'
            self.run1.setup_time = '20:00'
            self.run1.clean()
        self.run1.refresh_from_db()
        with self.subTest('bad anchor order'), self.assertRaises(ValidationError):
            self.run2.anchor_time = self.run3.anchor_time + datetime.timedelta(
                minutes=5
            )
            self.run2.clean()
        self.run2.refresh_from_db()
        with self.subTest('setup time correction'):
            self.run2.setup_time = '2:00'
            self.run2.save()
            self.run2.refresh_from_db()
            self.assertEqual(self.run2.setup_time, '0:05:00')
            self.run3.refresh_from_db()
            self.assertEqual(self.run3.starttime, self.run3.anchor_time)
            self.run3.anchor_time += datetime.timedelta(minutes=5)
            self.run3.save()
            self.run2.refresh_from_db()
            self.assertEqual(self.run2.setup_time, '0:10:00')
            self.run1.setup_time = '10:00'
            self.run1.save()
            self.run2.refresh_from_db()
            self.assertEqual(self.run2.setup_time, '0:05:00')
            self.run2.run_time = '17:00'
            self.run2.clean()
            self.run2.save()
            self.run2.refresh_from_db()
            self.assertEqual(self.run2.setup_time, '0:03:00')
        with self.subTest('bad anchor time'), self.assertRaises(ValidationError):
            self.run3.anchor_time -= datetime.timedelta(days=1)
            self.run3.clean()


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

    def test_too_long_for_anchor(self):
        from tracker.views.commands import MoveSpeedRun

        self.run2.anchor_time = self.run2.starttime
        self.run2.save()

        output, status = MoveSpeedRun(
            {'moving': self.run3.id, 'other': self.run2.id, 'before': True}
        )

        self.assertEqual(status, 400)


class TestSpeedRunAdmin(TransactionTestCase):
    def setUp(self):
        self.event1 = models.Event.objects.create(
            datetime=today_noon,
            targetamount=5,
            timezone=zoneinfo.ZoneInfo(
                getattr(settings, 'TIME_ZONE', 'America/Denver')
            ),
        )
        self.run1 = models.SpeedRun.objects.create(
            name='Test Run 1', run_time='0:45:00', setup_time='0:05:00', order=1
        )
        self.run2 = models.SpeedRun.objects.create(
            name='Test Run 2', run_time='0:15:00', setup_time='0:05:00', order=2
        )
        self.run3 = models.SpeedRun.objects.create(
            name='Test Run 3',
            run_time='0:35:00',
            setup_time='0:05:00',
            anchor_time=today_noon + datetime.timedelta(minutes=90),
            order=3,
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
                'run_id': self.run2.id,
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.run1.refresh_from_db()
        self.assertEqual(self.run1.run_time, '0:41:20')
        self.assertEqual(self.run1.setup_time, '0:09:40')

    @skipIf(
        django.VERSION < (4, 1),
        'assertFormError requires response object until Django 4.1',
    )
    def test_invalid_time(self):
        from tracker.admin.forms import StartRunForm

        form = StartRunForm(
            initial={
                'run_id': self.run2.id,
            },
            data={
                'run_time': '0:41:20',
                'start_time': '%s 11:21:00' % self.event1.date,
                'run_id': self.run2.id,
            },
        )
        self.assertFalse(form.is_valid())
        self.assertFormError(form, None, StartRunForm.Errors.invalid_start_time)

    @skipIf(
        django.VERSION < (4, 1),
        'assertFormError requires response object until Django 4.1',
    )
    def test_anchor_drift(self):
        from tracker.admin.forms import StartRunForm

        form = StartRunForm(
            initial={
                'run_id': self.run2.id,
            },
            data={
                'run_time': '0:41:20',
                'start_time': '%s 13:21:00' % self.event1.date,
                'run_id': self.run2.id,
            },
        )
        self.assertFalse(form.is_valid())
        self.assertFormError(form, None, StartRunForm.Errors.anchor_time_drift)


class TestSpeedrunList(TransactionTestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand, start_time=today_noon)
        self.event.save()

    def test_run_event_list(self):
        resp = self.client.get(
            reverse(
                'tracker:runindex',
            )
        )
        self.assertContains(resp, self.event.name)
        self.assertContains(resp, reverse('tracker:runindex', args=(self.event.short,)))
