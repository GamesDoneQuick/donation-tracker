import datetime
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase

from . import MigrationsTestCase
from .. import models

noon = datetime.time(12, 0)
today = datetime.date.today()
today_noon = datetime.datetime.combine(today, noon)
tomorrow = today + datetime.timedelta(days=1)
tomorrow_noon = datetime.datetime.combine(tomorrow, noon)
long_ago = today - datetime.timedelta(days=180)
long_ago_noon = datetime.datetime.combine(long_ago, noon)


class TestEvent(TestCase):
    def setUp(self):
        self.event = models.Event.objects.create(targetamount=1, datetime=today_noon)
        self.run = models.SpeedRun.objects.create(
            event=self.event,
            starttime=today_noon,
            order=0,
            run_time='00:01:00',
            setup_time='00:01:00',
        )

    def test_update_first_run_if_event_time_changes(self):
        self.event.datetime = tomorrow_noon
        self.event.save()
        self.run.refresh_from_db()
        self.assertEqual(self.run.starttime, self.event.datetime)

        self.event.datetime = long_ago_noon
        self.event.save()
        self.run.refresh_from_db()
        self.assertEqual(self.run.starttime, self.event.datetime)


class TestEventAdmin(TestCase):
    def setUp(self):
        self.super_user = User.objects.create_superuser(
            'admin', 'admin@example.com', 'password'
        )
        self.event = models.Event.objects.create(targetamount=5, datetime=today_noon)
        self.postbackurl = models.PostbackURL.objects.create(event=self.event)
        self.run = models.SpeedRun.objects.create(event=self.event)
        self.runner = models.Runner.objects.create()

    def test_event_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_event_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_event_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_event_change', args=(self.event.id,))
        )
        self.assertEqual(response.status_code, 200)

    def test_run_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_speedrun_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_speedrun_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_speedrun_change', args=(self.run.id,))
        )
        self.assertEqual(response.status_code, 200)

    def test_runner_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_runner_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_runner_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_runner_change', args=(self.runner.id,))
        )
        self.assertEqual(response.status_code, 200)

    def test_postbackurl_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_postbackurl_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_postbackurl_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_postbackurl_change', args=(self.postbackurl.id,))
        )
        self.assertEqual(response.status_code, 200)


class TestEventMigrations(MigrationsTestCase):
    migrate_from = '0002_add_event_datetime'
    migrate_to = '0003_backfill_event_datetime'

    def setUpBeforeMigration(self, apps):
        Event = apps.get_model('tracker', 'Event')
        SpeedRun = apps.get_model('tracker', 'SpeedRun')
        self.event1 = Event.objects.create(targetamount=5, date=today, short='event1')
        SpeedRun.objects.create(
            event=self.event1, starttime=today_noon - datetime.timedelta(minutes=30)
        )
        self.event2 = Event.objects.create(
            targetamount=5, date=tomorrow, short='event2'
        )

    def test_events_migrated(self):
        Event = self.apps.get_model('tracker', 'Event')
        event1 = Event.objects.get(pk=self.event1.id)
        event2 = Event.objects.get(pk=self.event2.id)
        self.assertEqual(
            event1.datetime,
            event1.timezone.localize(today_noon - datetime.timedelta(minutes=30)),
        )
        self.assertEqual(event2.datetime, event2.timezone.localize(tomorrow_noon))
