import functools
import os
import random
import time
from unittest import skipIf

from django.contrib.auth import get_user_model
from django.contrib.auth import models as auth_models
from django.test import TestCase
from django.urls import reverse
from selenium.common import StaleElementReferenceException
from selenium.webdriver.common.by import By

from tracker import models

from . import randgen
from .util import TrackerSeleniumTestCase, tomorrow_noon


class MergeDonorsViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_superuser(
            'superuser',
            'super@example.com',
            'password',
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


def retry(n_or_func):
    if isinstance(n_or_func, int):
        max_retries = n_or_func
    else:
        assert callable(n_or_func)
        max_retries = 10

    def _inner(wrapped):
        @functools.wraps(wrapped)
        def _inner2(*args, **kwargs):
            retries = 0
            while True:
                try:
                    n_or_func(*args, **kwargs)
                    break
                except StaleElementReferenceException:
                    retries += 1
                    # something is truly borked, but don't get stuck in an infinite loop
                    assert retries < max_retries, 'Too many retries on stale element'
                    time.sleep(1)

        return _inner2

    if callable(n_or_func):
        return _inner(n_or_func)
    else:
        return _inner


@skipIf(bool(int(os.environ.get('TRACKER_SKIP_SELENIUM', '0'))), 'selenium disabled')
class ProcessDonationsBidsBrowserTest(TrackerSeleniumTestCase):
    def setUp(self):
        User = get_user_model()
        self.rand = random.Random(None)
        self.superuser = User.objects.create_superuser(
            'superuser',
            'super@example.com',
            'password',
        )
        self.processor = User.objects.create(username='processor', is_staff=True)
        self.processor.set_password('password')
        self.processor.user_permissions.add(
            auth_models.Permission.objects.get(name='Can change donor'),
            auth_models.Permission.objects.get(name='Can change donation'),
            auth_models.Permission.objects.get(name='Can view all comments'),
            auth_models.Permission.objects.get(name='Can view bid'),
            auth_models.Permission.objects.get(name='Can view donation'),
            auth_models.Permission.objects.get(name='Can view donor'),
        )
        self.processor.save()
        self.head_processor = User.objects.create(
            username='head_processor', is_staff=True
        )
        self.head_processor.set_password('password')
        self.head_processor.user_permissions.add(
            auth_models.Permission.objects.get(name='Can approve or deny pending bids'),
            auth_models.Permission.objects.get(name='Can change donor'),
            auth_models.Permission.objects.get(name='Can change donation'),
            auth_models.Permission.objects.get(name='Can send donations to the reader'),
            auth_models.Permission.objects.get(name='Can view all comments'),
            auth_models.Permission.objects.get(name='Can view bid'),
            auth_models.Permission.objects.get(name='Can view donation'),
            auth_models.Permission.objects.get(name='Can view donor'),
        )
        self.head_processor.save()
        self.event = randgen.build_random_event(self.rand, start_time=tomorrow_noon)
        self.session = self.client.session
        self.session.save()
        self.donor = randgen.generate_donor(self.rand)
        self.donor.save()
        self.donation = randgen.generate_donation(
            self.rand, commentstate='PENDING', readstate='PENDING'
        )
        self.donation.save()
        parent, children = randgen.generate_bid(
            self.rand,
            event=self.event,
            allowuseroptions=True,
            max_depth=1,
            min_children=2,
            max_children=2,
            parent_state='OPENED',
            state='PENDING',
        )
        self.parent = parent
        self.parent.save()
        self.children = [children[0][0], children[1][0]]
        self.children[0].save()
        self.children[1].save()

    @retry
    def click_donation(self, donation_id, action='send'):
        self.webdriver.find_element(
            By.CSS_SELECTOR,
            f'div[data-test-pk="{donation_id}"] button[data-test-id="{action}"]',
        ).click()

    @retry
    def process_bid(self, bid_id, action):
        self.webdriver.find_element(
            By.CSS_SELECTOR,
            f'tr[data-test-pk="{bid_id}"] button[data-test-id="{action}"]',
        ).click()

    def test_one_step_screening(self):
        self.event.use_one_step_screening = True
        self.event.save()
        self.tracker_login(self.processor.username)
        self.webdriver.get(
            f'{self.live_server_url}{reverse("admin:process_donations")}'
        )
        self.click_donation(self.donation.pk)
        self.webdriver.find_element(By.CSS_SELECTOR, 'button[aria-name="undo"]')
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.readstate, 'READY')

    def test_two_step_screening(self):
        self.event.use_one_step_screening = False
        self.event.save()
        self.tracker_login(self.processor.username)
        self.webdriver.get(
            f'{self.live_server_url}{reverse("admin:process_donations")}'
        )
        self.click_donation(self.donation.pk)
        self.webdriver.find_element(By.CSS_SELECTOR, 'button[aria-name="undo"]')
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.readstate, 'FLAGGED')
        self.tracker_logout()
        self.tracker_login(self.head_processor.username)
        self.webdriver.get(
            f'{self.live_server_url}{reverse("admin:process_donations")}'
        )
        self.select_option('[data-test-id="processing-mode"]', 'confirm')
        self.click_donation(self.donation.pk)
        self.webdriver.find_element(By.CSS_SELECTOR, 'button[aria-name="undo"]')
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.readstate, 'READY')

    def test_bid_screening(self):
        self.tracker_login(self.head_processor.username)
        self.webdriver.get(
            f'{self.live_server_url}{reverse("admin:tracker_ui", kwargs={"extra": f"process_pending_bids/{self.event.pk}"})}'
        )
        self.process_bid(self.children[0].pk, 'accept')
        self.process_bid(self.children[1].pk, 'deny')
        self.webdriver.find_element(
            By.CSS_SELECTOR,
            f'tr[data-test-pk="{self.children[0].pk}"] td[data-test-state="OPENED"]',
        )
        self.webdriver.find_element(
            By.CSS_SELECTOR,
            f'tr[data-test-pk="{self.children[1].pk}"] td[data-test-state="DENIED"]',
        )
        self.children[0].refresh_from_db()
        self.children[1].refresh_from_db()
        self.assertEqual(self.children[0].state, 'OPENED')
        self.assertEqual(self.children[1].state, 'DENIED')


class TestAdminViews(TestCase):
    # smoke tests for other views that don't have more detailed tests yet
    def setUp(self):
        User = get_user_model()
        self.rand = random.Random(None)
        self.superuser = User.objects.create_superuser(
            'superuser',
            'super@example.com',
            'password',
        )
        self.search_user = User.objects.create(username='search', is_staff=True)
        self.search_user.user_permissions.add(
            auth_models.Permission.objects.get(codename='can_search_for_user')
        )
        self.other_user = User.objects.create(username='other', is_staff=True)
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

    def test_user_autocomplete(self):
        # needs to look real or the view will reject it
        data = {
            'app_label': 'tracker',
            'model_name': 'event',
            'field_name': 'prizecoordinator',
        }

        self.client.force_login(self.search_user)
        response = self.client.get(
            reverse('admin:tracker_user_autocomplete'), data=data
        )
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.other_user)
        response = self.client.get(
            reverse('admin:tracker_user_autocomplete'), data=data
        )
        self.assertEqual(response.status_code, 403)
