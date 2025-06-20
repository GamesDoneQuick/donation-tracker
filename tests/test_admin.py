import functools
import os
import random
import time
from unittest import skipIf

import django
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.auth import get_user_model
from django.contrib.auth import models as auth_models
from django.forms import ModelChoiceField
from django.test import RequestFactory, TestCase
from django.urls import reverse
from selenium.common import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.by import By

from tracker import models
from tracker.admin.bid import BidAdmin
from tracker.admin.filters import RunEventListFilter

from . import randgen
from .util import (
    AssertionHelpers,
    TrackerSeleniumTestCase,
    long_ago_noon,
    today_noon,
    tomorrow_noon,
)


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
                    wrapped(*args, **kwargs)
                    break
                except (
                    ElementClickInterceptedException,
                    StaleElementReferenceException,
                ):
                    retries += 1
                    # something is truly borked, but don't get stuck in an infinite loop
                    assert (
                        retries < max_retries
                    ), 'Too many retries on stale or unclickable element'
                    time.sleep(min(2 ** (retries - 1), 16))

        return _inner2

    if callable(n_or_func):
        return _inner(n_or_func)
    else:
        return _inner


@skipIf(bool(int(os.environ.get('TRACKER_SKIP_SELENIUM', '0'))), 'selenium disabled')
class ProcessDonationsAndBidsBrowserTest(TrackerSeleniumTestCase):
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
            f'div[data-testid="donation-{donation_id}"] button[data-testid="action-{action}"]',
        ).click()

    @retry
    def process_bid(self, bid_id, action):
        self.webdriver.find_element(
            By.CSS_SELECTOR,
            f'tr[data-testid="bid-{bid_id}"] button[data-testid="action-{action}"]',
        ).click()

    def test_host_only(self):
        self.event.screening_mode = 'host_only'
        self.event.save()
        self.tracker_login(self.processor.username)
        self.webdriver.get(
            f'{self.live_server_url}{reverse("admin:process_donations")}'
        )
        self.click_donation(self.donation.pk, 'read')
        # FIXME: what element can we look for?
        time.sleep(1)
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.readstate, 'READ')
        self.assertEqual(self.donation.commentstate, 'APPROVED')

    def test_one_pass_screening(self):
        self.event.screening_mode = 'one_pass'
        self.event.save()
        self.tracker_login(self.processor.username)
        self.webdriver.get(
            f'{self.live_server_url}{reverse("admin:process_donations")}'
        )
        self.click_donation(self.donation.pk)
        self.webdriver.find_element(By.CSS_SELECTOR, 'button[aria-name="undo"]')
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.readstate, 'READY')
        self.assertEqual(self.donation.commentstate, 'APPROVED')

    def test_two_pass_screening(self):
        self.event.screening_mode = 'two_pass'
        self.event.save()
        self.tracker_login(self.processor.username)
        self.webdriver.get(
            f'{self.live_server_url}{reverse("admin:process_donations")}'
        )
        self.click_donation(self.donation.pk)
        self.webdriver.find_element(By.CSS_SELECTOR, 'button[aria-name="undo"]')
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.readstate, 'FLAGGED')
        self.assertEqual(self.donation.commentstate, 'APPROVED')
        self.tracker_logout()
        self.tracker_login(self.head_processor.username)
        self.webdriver.get(
            f'{self.live_server_url}{reverse("admin:process_donations")}'
        )
        self.select_stately_option('[data-testid="processing-mode"]', 'confirm')
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
            f'tr[data-testid="bid-{self.children[0].pk}"] td[data-testid="state-OPENED"]',
        )
        self.webdriver.find_element(
            By.CSS_SELECTOR,
            f'tr[data-testid="bid-{self.children[1].pk}"] td[data-testid="state-DENIED"]',
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


class TestAdminFilters(TestCase):
    def setUp(self):
        self.rand = random.Random()
        self.factory = RequestFactory()

    def test_run_event_filter(self):
        event = randgen.generate_event(self.rand, today_noon)
        event.save()
        other_event = randgen.generate_event(self.rand, tomorrow_noon)
        other_event.save()
        runs = randgen.generate_runs(self.rand, event, 5, ordered=True)
        other_runs = randgen.generate_runs(self.rand, other_event, 5, ordered=True)
        bid = randgen.generate_bid(self.rand, run=runs[0], allow_children=False)[0]
        bid.save()
        event_bid = randgen.generate_bid(self.rand, event=event, allow_children=False)[
            0
        ]
        event_bid.save()
        other_bid = randgen.generate_bid(
            self.rand, event=other_event, allow_children=False
        )[0]
        other_bid.save()
        request = self.factory.get('/whatever')
        f = RunEventListFilter(request, {}, models.Bid, BidAdmin)
        self.assertEqual(f.lookups(request, BidAdmin), [])
        request = self.factory.get('/whatever', {'event__id__exact': event.id})
        f = RunEventListFilter(request, {}, models.Bid, BidAdmin)
        self.assertEqual(
            f.lookups(request, BidAdmin),
            [*((r.id, r.name) for r in runs), RunEventListFilter.EVENT_WIDE],
        )
        self.assertQuerySetEqual(
            f.queryset(request, models.Bid.objects.filter(event=event)),
            models.Bid.objects.filter(event=event),
        )
        request = self.factory.get('/whatever', {'event__id__exact': other_event.id})
        f = RunEventListFilter(request, {}, models.Bid, BidAdmin)
        self.assertEqual(
            f.lookups(request, BidAdmin),
            [*((r.id, r.name) for r in other_runs), RunEventListFilter.EVENT_WIDE],
        )
        self.assertQuerySetEqual(
            f.queryset(request, models.Bid.objects.filter(event=other_event)),
            models.Bid.objects.filter(event=other_event),
        )
        request = self.factory.get(
            '/whatever', {'event__id__exact': event.id, 'run': runs[0].id}
        )
        f = RunEventListFilter(request, {'run': str(runs[0].id)}, models.Bid, BidAdmin)
        self.assertQuerySetEqual(
            f.queryset(request, models.Bid.objects.filter(event=event)),
            models.Bid.objects.filter(event=event, speedrun=runs[0]),
        )
        request = self.factory.get(
            '/whatever', {'event__id__exact': event.id, 'run': '-'}
        )
        f = RunEventListFilter(request, {'run': '-'}, models.Bid, BidAdmin)
        self.assertQuerySetEqual(
            f.queryset(request, models.Bid.objects.filter(event=event)),
            models.Bid.objects.filter(event=event, speedrun=None),
        )
        with self.assertRaises(IncorrectLookupParameters):
            request = self.factory.get(
                '/whatever', {'event__id__exact': 'foo', 'run': '-'}
            )
            RunEventListFilter(request, {'run': '-'}, models.Bid, BidAdmin)
        with self.assertRaises(IncorrectLookupParameters):
            request = self.factory.get(
                '/whatever', {'event__id__exact': event.id, 'run': 'foo'}
            )
            RunEventListFilter(request, {'run': 'foo'}, models.Bid, BidAdmin).queryset(
                request, models.Bid.objects.all()
            )


class TestEventArchivedMixin(TestCase, AssertionHelpers):
    def setUp(self):
        self.factory = RequestFactory()
        self.super_user = auth_models.User.objects.create_superuser('superuser')
        self.rand = random.Random()
        self.event = randgen.generate_event(self.rand, today_noon)
        self.event.save()
        self.run = randgen.generate_run(self.rand, self.event)
        self.run.save()
        self.archived_event = randgen.generate_event(self.rand, long_ago_noon)
        self.archived_event.archived = True
        self.archived_event.save()
        self.archived_run = randgen.generate_run(self.rand, self.archived_event)
        self.archived_run.save()

    @skipIf(
        django.VERSION >= (5, 1, 0),
        'delete_selected is broken for certain models on 4.2',
    )
    def test_delete_selected_disabled(self):
        self.client.force_login(self.super_user)
        response = self.client.get(
            reverse('admin:tracker_speedrun_changelist'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            'delete_selected',
            (c[0] for c in response.context['action_form'].fields['action'].choices),
        )

    @skipIf(
        django.VERSION < (5, 1, 0),
        'delete_selected is broken for certain models on 4.2',
    )
    def test_delete_selected(self):
        self.client.force_login(self.super_user)
        response = self.client.post(
            reverse('admin:tracker_speedrun_changelist'),
            data={
                'action': 'delete_selected',
                ACTION_CHECKBOX_NAME: [self.run.id, self.archived_run.id],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Speed Run on Archived Event', response.context['perms_lacking'])
        response = self.client.post(
            reverse('admin:tracker_speedrun_changelist'),
            data={
                'action': 'delete_selected',
                ACTION_CHECKBOX_NAME: [self.run.id, self.archived_run.id],
                'post': 'yes',
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertQuerySetEqual(
            models.SpeedRun.objects.all(), {self.run, self.archived_run}, ordered=False
        )
        response = self.client.post(
            reverse('admin:tracker_speedrun_changelist'),
            data={
                'action': 'delete_selected',
                ACTION_CHECKBOX_NAME: [self.run.id],
                'post': 'yes',
            },
        )
        self.assertRedirects(response, reverse('admin:tracker_speedrun_changelist'))
        self.assertMessages(response, ['Successfully deleted 1 Speed Run.'])
        self.assertQuerySetEqual(
            models.SpeedRun.objects.all(), {self.archived_run}, ordered=False
        )


class TestReadOnlyEventMixin(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.super_user = auth_models.User.objects.create_superuser('superuser')
        self.rand = random.Random()
        self.event = randgen.generate_event(self.rand, today_noon)
        self.event.save()
        self.milestone = randgen.generate_milestone(self.rand, self.event)
        self.milestone.save()
        self.other_milestone = randgen.generate_milestone(self.rand, self.event)
        self.other_milestone.amount = self.milestone.amount + 5
        self.other_milestone.save()

    # not specific to Milestones, but it's an admin that uses it
    def test_add_form(self):
        self.client.force_login(self.super_user)
        resp = self.client.get(reverse('admin:tracker_milestone_add'))
        event_field = resp.context['adminform'].fields['event']
        self.assertIsInstance(event_field, ModelChoiceField)
        self.assertFalse(event_field.disabled)
        resp = self.client.post(
            reverse('admin:tracker_milestone_add'),
            data={
                'event': self.event.id,
                'name': self.milestone.name,
                'amount': self.milestone.amount + 20,
                'start': self.milestone.start,
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.resolver_match.url_name.endswith('changelist'))

    def test_change_form(self):
        self.client.force_login(self.super_user)
        resp = self.client.get(
            reverse('admin:tracker_milestone_change', args=(self.milestone.id,))
        )
        self.assertIn('event', resp.context['adminform'].readonly_fields)
        resp = self.client.post(
            reverse('admin:tracker_milestone_change', args=(self.milestone.id,)),
            data={
                'name': self.milestone.name,
                'amount': self.milestone.amount,
                'start': self.milestone.start,
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.resolver_match.url_name.endswith('changelist'))
        # this will potentially raise IntegrityError if the form does not validate properly
        resp = self.client.post(
            reverse('admin:tracker_milestone_change', args=(self.milestone.id,)),
            data={
                'name': self.milestone.name,
                'amount': self.other_milestone.amount,
                'start': self.milestone.start,
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.resolver_match.url_name.endswith('change'))
        self.assertFormError(
            resp.context['adminform'],
            None,
            'Milestone with this Event and Amount already exists.',
        )
