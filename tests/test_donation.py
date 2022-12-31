# coding: utf-8

import datetime
from decimal import Decimal
from unittest.mock import patch

from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from tracker import models

from .util import today_noon, tomorrow_noon


class TestDonation(TestCase):
    def setUp(self):
        self.event = models.Event.objects.create(
            receivername='Médecins Sans Frontières',
            targetamount=1,
            datetime=datetime.datetime(2018, 1, 1),
        )

    def test_anonymous(self):
        # Anonymous donation is anonymous
        donation = models.Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            domain='PAYPAL',
            requestedvisibility='ANON',
            event=self.event,
        )
        self.assertTrue(donation.anonymous())

        # Donation from an anonymous donor with CURR is anonymous
        donation = models.Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            domain='PAYPAL',
            requestedvisibility='CURR',
            donor=models.Donor(visibility='ANON'),
            event=self.event,
        )
        self.assertTrue(donation.anonymous())

        # Donation from a non-anonymous donor with CURR is not anonymous
        donation = models.Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            domain='PAYPAL',
            requestedvisibility='CURR',
            donor=models.Donor(visibility='ALIAS'),
            event=self.event,
        )
        self.assertFalse(donation.anonymous())

    def test_approve_if_anonymous_and_no_comment(self):
        alias_donor = models.Donor.objects.create(visibility='ALIAS', alias='FooBar')
        anon_donor = models.Donor.objects.create(visibility='ANON')

        # If the comment was already read (or anything not pending), don't act
        donation = models.Donation.objects.create(
            timereceived=timezone.now(),
            readstate='READ',
            amount=Decimal(1.5),
            domain='PAYPAL',
            requestedvisibility='ANON',
            donor=anon_donor,
            event=self.event,
        )
        self.assertEqual(donation.readstate, 'READ')

        # With no threshold given, leave as is
        donation = models.Donation.objects.create(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            domain='PAYPAL',
            requestedvisibility='ANON',
            donor=anon_donor,
            event=self.event,
        )
        self.assertEqual(donation.readstate, 'PENDING')

        self.event.auto_approve_threshold = 5
        self.event.save()

        # With a threshold and a donation above it, send to reader
        donation = models.Donation.objects.create(
            timereceived=timezone.now(),
            amount=Decimal(10),
            domain='PAYPAL',
            requestedvisibility='CURR',
            donor=anon_donor,
            event=self.event,
        )
        self.assertEqual(donation.readstate, 'READY')

        # With a threshold and a donation below it, ignore
        donation = models.Donation.objects.create(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            domain='PAYPAL',
            requestedvisibility='ANON',
            donor=anon_donor,
            event=self.event,
        )
        self.assertEqual(donation.readstate, 'IGNORED')

        # Donation with a non-anonymous donor should not bypass screening
        donation = models.Donation.objects.create(
            timereceived=timezone.now(),
            amount=Decimal(10),
            domain='PAYPAL',
            requestedvisibility='ALIAS',
            donor=alias_donor,
            event=self.event,
        )
        self.assertEqual(donation.readstate, 'PENDING')

        # Donation with a comment should not bypass screening
        donation = models.Donation.objects.create(
            timereceived=timezone.now(),
            amount=Decimal(10),
            comment='Hello',
            domain='PAYPAL',
            requestedvisibility='ANON',
            donor=anon_donor,
            event=self.event,
        )
        self.assertEqual(donation.readstate, 'PENDING')

        # edge case: threshold of $0 still approves

        self.event.auto_approve_threshold = 0
        self.event.save()

        donation = models.Donation.objects.create(
            timereceived=timezone.now(),
            amount=Decimal(10),
            domain='PAYPAL',
            requestedvisibility='CURR',
            donor=anon_donor,
            event=self.event,
        )
        self.assertEqual(donation.readstate, 'READY')


class TestDonorAdmin(TestCase):
    def setUp(self):
        self.super_user = User.objects.create_superuser(
            'admin', 'admin@example.com', 'password'
        )
        self.event = models.Event.objects.create(
            short='ev1', name='Event 1', targetamount=5, datetime=today_noon
        )

        self.donor = models.Donor.objects.create(firstname='John', lastname='Doe')
        self.donation = models.Donation.objects.create(
            donor=self.donor, amount=5, event=self.event, transactionstate='COMPLETED'
        )

    def test_donation_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_donation_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_donation_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_donation_change', args=(self.donation.id,))
        )
        self.assertEqual(response.status_code, 200)

    @patch('tracker.tasks.post_donation_to_postbacks')
    @override_settings(HAS_CELERY=True)
    def test_donation_postback_with_celery(self, task):
        self.client.force_login(self.super_user)
        response = self.client.post(
            reverse('admin:tracker_donation_changelist'),
            {
                'action': 'send_donation_postbacks',
                ACTION_CHECKBOX_NAME: [self.donation.id],
            },
        )
        self.assertRedirects(response, reverse('admin:tracker_donation_changelist'))
        task.delay.assert_called_with(self.donation.id)
        task.assert_not_called()

    @patch('tracker.tasks.post_donation_to_postbacks')
    @override_settings(HAS_CELERY=False)
    def test_donation_postback_without_celery(self, task):
        self.client.force_login(self.super_user)
        response = self.client.post(
            reverse('admin:tracker_donation_changelist'),
            {
                'action': 'send_donation_postbacks',
                ACTION_CHECKBOX_NAME: [self.donation.id],
            },
        )
        self.assertRedirects(response, reverse('admin:tracker_donation_changelist'))
        task.assert_called_with(self.donation.id)
        task.delay.assert_not_called()


class TestDonationViews(TestCase):
    def setUp(self):
        self.super_user = User.objects.create_superuser(
            'admin', 'admin@example.com', 'password'
        )
        self.event = models.Event.objects.create(
            short='ev1', name='Event 1', targetamount=5, datetime=today_noon
        )
        self.other_event = models.Event.objects.create(
            short='ev2', name='Event 2', targetamount=5, datetime=tomorrow_noon
        )
        self.regular_donor = models.Donor.objects.create(
            alias='JohnDoe', visibility='ALIAS'
        )
        self.anonymous_donor = models.Donor.objects.create(visibility='ANON')
        self.regular_donation = models.Donation.objects.create(
            event=self.event,
            amount=5,
            donor=self.regular_donor,
            transactionstate='COMPLETED',
        )
        self.anonymous_donation = models.Donation.objects.create(
            event=self.event,
            amount=15,
            donor=self.anonymous_donor,
            transactionstate='COMPLETED',
        )
        self.other_donation = models.Donation.objects.create(
            event=self.other_event,
            amount=25,
            donor=self.regular_donor,
            transactionstate='COMPLETED',
        )

    def test_donation_list_no_event(self):
        resp = self.client.get(reverse('tracker:donationindex'))
        self.assertContains(
            resp,
            '<small>Total (Count): $45.00 (3) &mdash; Max/Avg/Median Donation: $25.00/$15.00/$15.00</small>',
            html=True,
        )
        self.assertContains(resp, self.regular_donor.visible_name())
        self.assertContains(resp, self.regular_donor.get_absolute_url())
        self.assertContains(resp, self.anonymous_donor.visible_name())
        self.assertNotContains(resp, self.anonymous_donor.get_absolute_url())
        self.assertNotContains(resp, 'Invalid Variable')

    def test_donation_list_with_event(self):
        resp = self.client.get(reverse('tracker:donationindex', args=(self.event.id,)))
        self.assertContains(
            resp,
            '<small>Total (Count): $20.00 (2) &mdash; Max/Avg/Median Donation: $15.00/$10.00/$10.00</small>',
            html=True,
        )
        self.assertContains(resp, self.regular_donor.visible_name())
        self.assertContains(
            resp,
            self.regular_donor.cache_for(self.event.id).get_absolute_url(),
        )
        self.assertContains(resp, self.anonymous_donor.visible_name())
        self.assertNotContains(
            resp, self.anonymous_donor.cache_for(self.event.id).get_absolute_url()
        )
        self.assertNotContains(resp, 'Invalid Variable')
