import datetime
import random
import zoneinfo

from django.contrib.auth.models import User
from django.core import management
from django.core.exceptions import ValidationError
from django.test import TransactionTestCase
from django.urls import reverse

import tracker.models as models
import tracker.models.tag
from tracker import settings

from . import randgen
from .util import MigrationsTestCase, today_noon


class TestSpeedRunBase(TransactionTestCase):
    def setUp(self):
        super().setUp()
        if not hasattr(self, 'event'):
            self.event = models.Event.objects.create(datetime=today_noon)
        self.run1 = models.SpeedRun.objects.create(
            event=self.event,
            name='Test Run',
            run_time='45:00',
            setup_time='5:00',
            order=1,
        )
        self.run2 = models.SpeedRun.objects.create(
            event=self.event,
            name='Test Run 2',
            run_time='15:00',
            setup_time='5:00',
            order=2,
        )
        self.run3 = models.SpeedRun.objects.create(
            event=self.event, name='Test Run 3', run_time='5:00', order=3
        )
        self.run4 = models.SpeedRun.objects.create(
            event=self.event,
            name='Test Run 4',
            run_time='1:20:00',
            setup_time='5:00',
            order=None,
        )
        self.run5 = models.SpeedRun.objects.create(
            event=self.event, name='Test Run 5', order=4, run_time='15:00'
        )
        self.runner1 = models.Talent.objects.create(name='trihex')
        self.runner2 = models.Talent.objects.create(name='neskamikaze')
        self.headset1 = models.Talent.objects.create(name='SpikeVegeta')
        self.headset2 = models.Talent.objects.create(name='puwexil')
        link_type = models.VideoLinkType.objects.create(name='youtube')
        self.video_link1 = models.VideoLink.objects.create(
            run=self.run2, link_type=link_type, url='https://youtu.be/deadbeef'
        )
        self.tag1 = tracker.models.tag.Tag.objects.create(name='foo')
        self.tag2 = tracker.models.tag.Tag.objects.create(name='bar')


class TestSpeedRun(TestSpeedRunBase):
    # TODO: maybe disallow partial seconds? this cropped as a bug but we never actually use milliseconds

    def test_timestamps(self):
        self.run1.run_time = '45:00.1'
        self.run1.setup_time = 300000
        self.run1.save()
        self.assertEqual(self.run1.run_time, '0:45:00.100')
        self.assertEqual(self.run1.setup_time, '0:05:00')

    def test_first_run_start_time(self):
        self.assertEqual(self.run1.starttime, self.event.datetime)

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

    def test_null_order(self):
        self.assertEqual(self.run4.starttime, None)
        self.assertEqual(self.run4.endtime, None)

    def test_ordered_needs_run_or_setup_time(self):
        with self.assertRaises(ValidationError):
            self.run5.run_time = '0'
            self.run5.setup_time = '0'
            self.run5.full_clean()

        self.run5.setup_time = '5:00'
        self.run5.full_clean()

        self.run5.run_time = '5:00'
        self.run5.setup_time = '0'
        self.run5.full_clean()

    def test_removing_first_run_from_schedule(self):
        self.run1.order = None
        self.run1.save()
        self.run2.refresh_from_db()
        self.assertEqual(self.run2.order, 1)
        self.assertEqual(self.run2.starttime, self.event.datetime)

    def test_removing_run_from_middle_of_schedule(self):
        old_order = self.run3.order
        self.run3.order = None
        self.run3.save()
        self.run5.refresh_from_db()
        self.assertEqual(self.run5.order, old_order)
        self.assertEqual(self.run5.starttime, self.run2.endtime)

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

    def test_tags(self):
        with self.subTest('priority tag auto adds to list'):
            self.run1.tags.add(self.tag2)
            self.run1.priority_tag = self.tag1
            self.run1.save()
            self.assertSetEqual(set(self.run1.tags.all()), {self.tag1, self.tag2})


class TestSpeedRunAdmin(TransactionTestCase):
    def setUp(self):
        self.event1 = models.Event.objects.create(
            datetime=today_noon,
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
        from tracker.admin.forms import StartRunForm

        self.client.login(username='admin', password='password')
        with self.subTest('normal run'):
            cf = f'event__id__exact={self.event1.pk}'
            resp = self.client.post(
                reverse('admin:start_run', args=(self.run2.id,)),
                data={
                    'run_time': '0:41:20',
                    'start_time': '%s 12:51:00' % self.event1.date,
                    'run_id': self.run2.id,
                    '_changelist_filters': cf,
                },
            )
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(
                resp['Location'],
                reverse('admin:tracker_speedrun_changelist') + '?' + cf,
            )
            self.run1.refresh_from_db()
            self.assertEqual(self.run1.run_time, '0:41:20')
            self.assertEqual(self.run1.setup_time, '0:09:40')
        with self.subTest('drift failure'):
            resp = self.client.post(
                reverse('admin:start_run', args=(self.run2.id,)),
                data={
                    'run_time': '0:41:20',
                    'start_time': '%s 13:25:00' % self.event1.date,
                    'run_id': self.run2.id,
                },
            )
            self.assertEqual(resp.status_code, 200)
            self.assertFormError(
                resp.context['form'], None, StartRunForm.Errors.anchor_time_drift
            )
        with self.subTest('anchored run'):
            resp = self.client.post(
                reverse('admin:start_run', args=(self.run3.id,)),
                data={
                    'run_time': '0:13:20',
                    'start_time': '%s 13:35:00' % self.event1.date,
                    'run_id': self.run3.id,
                },
            )
            self.assertEqual(resp.status_code, 302)
            self.run2.refresh_from_db()
            self.assertEqual(self.run2.run_time, '0:13:20')
            self.assertEqual(self.run2.setup_time, '0:30:40')
            self.run3.refresh_from_db()
            expected_start = datetime.datetime.combine(
                self.event1.date, datetime.time(13, 35), tzinfo=self.event1.timezone
            )
            self.assertEqual(self.run3.anchor_time, expected_start)
            self.assertEqual(self.run3.starttime, expected_start)

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


class TestRemoveDeprecatedRunnersMigration(MigrationsTestCase):
    migrate_from = [('tracker', '0057_remove_category_nulls')]
    migrate_to = [('tracker', '0058_remove_deprecated_runners')]
    expected_migration_error_class = management.CommandError

    def setUpBeforeMigration(self, apps):
        Event = apps.get_model('tracker', 'Event')
        SpeedRun = apps.get_model('tracker', 'SpeedRun')
        Talent = apps.get_model('tracker', 'Talent')
        self.event = Event.objects.create(
            short='test', name='Test Event', datetime=today_noon
        )
        self.run = SpeedRun.objects.create(event=self.event, name='Test Run')
        self.talent = Talent.objects.create(name='New Name')
        self.run.runners.add(self.talent)

        self.run.deprecated_runners = 'Old Name'
        self.run.save()

    def tearDownBeforeFinalMigration(self, apps):
        SpeedRun = apps.get_model('tracker', 'SpeedRun')
        self.run = SpeedRun.objects.get(id=self.run.id)
        self.run.deprecated_runners = 'New Name'
        self.run.save()

    def test_migration_error(self):
        self.assertIsInstance(self.migration_error, management.CommandError)
        for n in ['New Name', 'Old Name']:
            self.assertIn(n.lower(), str(self.migration_error))
