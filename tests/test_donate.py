from decimal import Decimal

from django.test import TransactionTestCase
from django.urls import reverse

import tracker.forms as forms
import tracker.models as models

from .util import long_ago_noon, today_noon, tomorrow_noon


class TestDonorNameAssignment(TransactionTestCase):
    def testAliasAnonToVisibilityAnon(self):
        data = {
            'amount': Decimal('5.00'),
            'requestedvisibility': 'ALIAS',
            'requestedalias': 'Anonymous',
            'requestedsolicitemail': 'CURR',
        }
        form = forms.DonationEntryForm(data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['requestedvisibility'], 'ANON')
        self.assertFalse(bool(form.cleaned_data['requestedalias']))


class TestDonateViews(TransactionTestCase):
    def setUp(self):
        self.normal_event = models.Event.objects.create(
            short='normal', name='Normal', datetime=today_noon
        )
        self.upcoming_event = models.Event.objects.create(
            short='upcoming',
            name='Upcoming',
            datetime=tomorrow_noon,
            allow_donations=False,
        )
        self.locked_event = models.Event.objects.create(
            short='locked',
            name='Locked',
            datetime=long_ago_noon,
            locked=True,
        )

    def testNormalEvent(self):
        resp = self.client.get(reverse('tracker:donate', args=(self.normal_event.id,)))
        self.assertRedirects(
            resp,
            reverse('tracker:ui:donate', args=(self.normal_event.id,)),
            status_code=301,
        )

        resp = self.client.get(
            reverse('tracker:ui:donate', args=(self.normal_event.id,))
        )
        self.assertEqual(resp.status_code, 200)

    def testUpcomingEvent(self):
        resp = self.client.get(
            reverse('tracker:donate', args=(self.upcoming_event.id,))
        )
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(
            reverse('tracker:ui:donate', args=(self.upcoming_event.id,))
        )
        self.assertEqual(resp.status_code, 404)

    def testLockedEvent(self):
        resp = self.client.get(reverse('tracker:donate', args=(self.locked_event.id,)))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(
            reverse('tracker:ui:donate', args=(self.locked_event.id,))
        )
        self.assertEqual(resp.status_code, 404)
