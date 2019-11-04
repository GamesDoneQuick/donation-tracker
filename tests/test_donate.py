import datetime
from django.urls import reverse

import tracker.models as models
import tracker.forms as forms

from django.test import TestCase, TransactionTestCase

from decimal import Decimal

noon = datetime.time(12, 0)
today = datetime.date.today()
today_noon = datetime.datetime.combine(today, noon)
tomorrow = today + datetime.timedelta(days=1)
tomorrow_noon = datetime.datetime.combine(tomorrow, noon)
long_ago = today - datetime.timedelta(days=180)
long_ago_noon = datetime.datetime.combine(long_ago, noon)


class TestDonorNameAssignment(TransactionTestCase):
    def testAliasAnonToVisibilityAnon(self):
        data = {
            "amount": Decimal("5.00"),
            "requestedvisibility": "ALIAS",
            "requestedalias": "Anonymous",
            "requestedsolicitemail": "CURR",
        }
        form = forms.DonationEntryForm(data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["requestedvisibility"], "ANON")
        self.assertFalse(bool(form.cleaned_data["requestedalias"]))


class TestDonateViews(TransactionTestCase):
    def setUp(self):
        self.normal_event = models.Event.objects.create(
            targetamount=5, short="normal", name="Normal", datetime=today_noon
        )
        self.upcoming_event = models.Event.objects.create(
            targetamount=5,
            short="upcoming",
            name="Upcoming",
            datetime=tomorrow_noon,
            allow_donations=False,
        )
        self.locked_event = models.Event.objects.create(
            targetamount=5,
            short="locked",
            name="Locked",
            datetime=long_ago_noon,
            locked=True,
        )

    def testNormalEvent(self):
        resp = self.client.get(reverse("tracker:donate", args=(self.normal_event.id,)))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(
            reverse("tracker:ui:donate", args=(self.normal_event.id,))
        )
        self.assertEqual(resp.status_code, 200)

    def testUpcomingEvent(self):
        resp = self.client.get(
            reverse("tracker:donate", args=(self.upcoming_event.id,))
        )
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(
            reverse("tracker:ui:donate", args=(self.upcoming_event.id,))
        )
        self.assertEqual(resp.status_code, 404)

    def testLockedEvent(self):
        resp = self.client.get(reverse("tracker:donate", args=(self.locked_event.id,)))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(
            reverse("tracker:ui:donate", args=(self.locked_event.id,))
        )
        self.assertEqual(resp.status_code, 404)
