from __future__ import print_function

import random

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.urlresolvers import reverse
from django.test import TestCase

from tracker import randgen
from tracker.models import Donor

User = get_user_model()


class MergeDonorsViewTests(TestCase):
    def setUp(self):
        User.objects.create_superuser(
            'superuser',
            'super@example.com',
            'password',
        )
        self.client.login(username='superuser', password='password')

    def tearDown(self):
        self.client.logout()

    def test_get_loads(self):
        d1 = Donor.objects.create()
        d2 = Donor.objects.create()
        ids = "{},{}".format(d1.pk, d2.pk)

        response = self.client.get(
            reverse('admin:merge_donors'), {'objects': ids})
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "Select which donor to use as the template")


class ProcessDonationsTest(TestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.superuser = User.objects.create_superuser(
            'superuser',
            'super@example.com',
            'password',
        )
        self.processor = User.objects.create(username='processor', is_staff=True)
        self.processor.user_permissions.add(Permission.objects.get(name='Can change donor'),
                                            Permission.objects.get(name='Can change donation'))
        self.head_processor = User.objects.create(username='head_processor', is_staff=True)
        self.head_processor.user_permissions.add(Permission.objects.get(name='Can change donor'),
                                                 Permission.objects.get(name='Can change donation'),
                                                 Permission.objects.get(name='Can send donations to the reader'))
        self.event = randgen.build_random_event(self.rand)
        self.session = self.client.session
        self.session['admin-event'] = self.event.id
        self.session.save()

    def test_no_event_selected_non_head(self):
        del self.session['admin-event']
        self.session.save()
        self.client.force_login(self.processor)
        response = self.client.get('/admin/process_donations')
        self.assertEqual(response.context['user_can_approve'], False)

    def test_no_event_selected_with_head(self):
        del self.session['admin-event']
        self.session.save()
        self.client.force_login(self.head_processor)
        response = self.client.get('/admin/process_donations')
        self.assertEqual(response.context['user_can_approve'], True)

    def test_one_step_screening(self):
        self.client.force_login(self.processor)
        response = self.client.get('/admin/process_donations')
        self.assertEqual(response.context['user_can_approve'], True)

    def test_two_step_screening_non_head(self):
        self.event.use_one_step_screening = False
        self.event.save()
        self.client.force_login(self.processor)
        response = self.client.get('/admin/process_donations')
        self.assertEqual(response.context['user_can_approve'], False)

    def test_two_step_screening_with_head(self):
        self.event.use_one_step_screening = False
        self.event.save()
        self.client.force_login(self.head_processor)
        response = self.client.get('/admin/process_donations')
        self.assertEqual(response.context['user_can_approve'], True)
