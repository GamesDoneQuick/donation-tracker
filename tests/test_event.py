import datetime
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase

from .. import models

class TestEventAdmin(TestCase):
    def setUp(self):
        self.super_user = User.objects.create_superuser('admin', 'admin@example.com', 'password')
        self.event = models.Event.objects.create(targetamount=5, date=datetime.date.today())
        self.postbackurl = models.PostbackURL.objects.create(event=self.event)
        self.run = models.SpeedRun.objects.create(event=self.event)
        self.runner = models.Runner.objects.create()

    def test_event_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_event_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_event_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_event_change', args=(self.event.id,)))
        self.assertEqual(response.status_code, 200)

    def test_run_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_speedrun_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_speedrun_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_speedrun_change', args=(self.run.id,)))
        self.assertEqual(response.status_code, 200)

    def test_runner_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_runner_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_runner_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_runner_change', args=(self.runner.id,)))
        self.assertEqual(response.status_code, 200)

    def test_postbackurl_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_postbackurl_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_postbackurl_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_postbackurl_change', args=(self.postbackurl.id,)))
        self.assertEqual(response.status_code, 200)
