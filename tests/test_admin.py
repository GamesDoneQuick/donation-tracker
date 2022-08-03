import random

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from tracker import models

from . import randgen
from .util import TrackerSeleniumTestCase

User = get_user_model()


class MergeDonorsViewTests(TestCase):
    def setUp(self):
        User.objects.create_superuser(
            'superuser', 'super@example.com', 'password',
        )
        self.client.login(username='superuser', password='password')

    def tearDown(self):
        self.client.logout()

    def test_get_loads(self):
        d1 = models.Donor.objects.create()
        d2 = models.Donor.objects.create()
        ids = '{},{}'.format(d1.pk, d2.pk)

        response = self.client.get(reverse('admin:merge_donors'), {'objects': ids})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select which donor to use as the template')


class ProcessDonationsBrowserTest(TrackerSeleniumTestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.superuser = User.objects.create_superuser(
            'superuser', 'super@example.com', 'password',
        )
        self.processor = User.objects.create(username='processor', is_staff=True)
        self.processor.set_password('password')
        self.processor.user_permissions.add(
            Permission.objects.get(name='Can change donor'),
            Permission.objects.get(name='Can change donation'),
            Permission.objects.get(name='Can view all comments'),
        )
        self.processor.save()
        self.head_processor = User.objects.create(
            username='head_processor', is_staff=True
        )
        self.head_processor.set_password('password')
        self.head_processor.user_permissions.add(
            Permission.objects.get(name='Can change donor'),
            Permission.objects.get(name='Can change donation'),
            Permission.objects.get(name='Can send donations to the reader'),
            Permission.objects.get(name='Can view all comments'),
        )
        self.head_processor.save()
        self.event = randgen.build_random_event(self.rand)
        self.session = self.client.session
        self.session.save()
        self.donor = randgen.generate_donor(self.rand)
        self.donor.save()
        self.donation = randgen.generate_donation(
            self.rand, commentstate='PENDING', readstate='PENDING'
        )
        self.donation.save()

    def test_one_step_screening(self):
        self.tracker_login(self.processor.username)
        self.webdriver.get(
            f'{self.live_server_url}{reverse("admin:tracker_ui")}/process_donations/{str(self.event.id)}'
        )
        self.wait_for_spinner()
        row = self.webdriver.find_element_by_css_selector(
            f'tr[data-test-pk="{self.donation.pk}"]'
        )
        row.find_element_by_css_selector('button[data-test-id="send"]').click()
        self.wait_for_spinner()
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.readstate, 'READY')

    def test_two_step_screening(self):
        self.event.use_one_step_screening = False
        self.event.save()
        self.tracker_login(self.processor.username)
        self.webdriver.get(
            f'{self.live_server_url}{reverse("admin:tracker_ui")}/process_donations/{str(self.event.id)}'
        )
        self.wait_for_spinner()
        row = self.webdriver.find_element_by_css_selector(
            f'tr[data-test-pk="{self.donation.pk}"]'
        )
        row.find_element_by_css_selector('button[data-test-id="send"]').click()
        self.wait_for_spinner()
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.readstate, 'FLAGGED')
        self.tracker_logout()
        self.tracker_login(self.head_processor.username)
        self.webdriver.get(
            f'{self.live_server_url}{reverse("admin:tracker_ui")}/process_donations/{str(self.event.id)}'
        )
        self.wait_for_spinner()
        self.select_option('[data-test-id="processing-mode"]', 'confirm')
        self.webdriver.find_element_by_css_selector(
            'button[data-test-id="refresh"'
        ).click()
        self.wait_for_spinner()
        row = self.webdriver.find_element_by_css_selector(
            f'tr[data-test-pk="{self.donation.pk}"]'
        )
        row.find_element_by_css_selector('button[data-test-id="send"]').click()
        self.wait_for_spinner()
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.readstate, 'READY')


class TestAdminViews(TestCase):
    # smoke tests for other views that don't have more detailed tests yet
    def setUp(self):
        self.rand = random.Random(None)
        self.superuser = User.objects.create_superuser(
            'superuser', 'super@example.com', 'password',
        )
        self.event = randgen.build_random_event(self.rand)
        self.session = self.client.session
        self.session.save()

    def test_merge_bids(self):
        self.client.force_login(self.superuser)
        randgen.generate_runs(self.rand, self.event, 5)
        randgen.generate_bids(self.rand, self.event, 10)
        response = self.client.get(
            reverse('admin:merge_bids'),
            {'objects': ','.join(str(b.id) for b in models.Bid.objects.all())},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select which bid to use as the template')

    def test_automail_prize_contributors(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('admin:automail_prize_contributors'))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse('admin:automail_prize_contributors', args=(self.event.short,))
        )
        self.assertEqual(response.status_code, 200)

    def test_automail_prize_winners(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('admin:automail_prize_winners'))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse('admin:automail_prize_winners', args=(self.event.short,))
        )
        self.assertEqual(response.status_code, 200)

    def test_automail_prize_accept_notifications(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('admin:automail_prize_accept_notifications'))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse(
                'admin:automail_prize_accept_notifications', args=(self.event.short,)
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_automail_prize_shipping_notifications(self):
        self.client.force_login(self.superuser)
        response = self.client.get(
            reverse('admin:automail_prize_shipping_notifications')
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse(
                'admin:automail_prize_shipping_notifications', args=(self.event.short,)
            )
        )
        self.assertEqual(response.status_code, 200)
