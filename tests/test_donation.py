# coding: utf-8

import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from tracker import models
from .util import today_noon, tomorrow_noon


class TestDonation(TestCase):
    def setUp(self):
        self.event = models.Event(
            receivername='Médecins Sans Frontières',
            targetamount=1,
            paypalemail='msf@example.com',
            paypalcurrency='USD',
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

    def test_anonymous_and_no_comment(self):
        alias_donor = models.Donor(visibility='ALIAS')
        anon_donor = models.Donor(visibility='ANON')

        # GOOD: Anonymous donation with no comment and any donor
        donation = models.Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            domain='PAYPAL',
            requestedvisibility='ANON',
            donor=alias_donor,
            event=self.event,
        )
        self.assertTrue(donation.anonymous_and_no_comment())

        # GOOD: Donation with no comment, CURR visibility, and anonymous donor
        donation = models.Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            domain='PAYPAL',
            requestedvisibility='CURR',
            donor=anon_donor,
            event=self.event,
        )
        self.assertTrue(donation.anonymous_and_no_comment())

        # BAD: Donation with no comment, but some non-anonymous visibility
        donation = models.Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            domain='PAYPAL',
            requestedvisibility='ALIAS',
            donor=anon_donor,
            event=self.event,
        )
        self.assertFalse(donation.anonymous_and_no_comment())
        donation.approve_if_anonymous_and_no_comment()
        self.assertEqual(donation.readstate, 'PENDING')

        # BAD: Donation with a comment
        donation = models.Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            comment='Hello',
            domain='PAYPAL',
            requestedvisibility='ANON',
            donor=anon_donor,
            event=self.event,
        )
        self.assertEqual(donation.readstate, 'PENDING')

    def test_approve_if_anonymous_and_no_comment(self):
        alias_donor = models.Donor(visibility='ALIAS')
        anon_donor = models.Donor(visibility='ANON')

        # If the comment was already read (or anything not pending), don't act
        donation = models.Donation(
            timereceived=timezone.now(),
            readstate='READ',
            amount=Decimal(1.5),
            domain='PAYPAL',
            requestedvisibility='ANON',
            donor=alias_donor,
            event=self.event,
        )
        donation.approve_if_anonymous_and_no_comment()
        self.assertEqual(donation.readstate, 'READ')

        # With no threshold given, just ignore
        donation = models.Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            domain='PAYPAL',
            requestedvisibility='ANON',
            donor=alias_donor,
            event=self.event,
        )
        donation.approve_if_anonymous_and_no_comment()
        self.assertEqual(donation.readstate, 'IGNORED')

        # With a threshold and a donation above it, send to reader
        donation = models.Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            domain='PAYPAL',
            requestedvisibility='CURR',
            donor=anon_donor,
            event=self.event,
        )
        donation.approve_if_anonymous_and_no_comment(1)
        self.assertEqual(donation.readstate, 'READY')

        # With a threshold and a donation below it, ignore
        donation = models.Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            domain='PAYPAL',
            requestedvisibility='ANON',
            donor=anon_donor,
            event=self.event,
        )
        donation.approve_if_anonymous_and_no_comment(5)
        self.assertEqual(donation.readstate, 'IGNORED')

        # Donation with a comment should not be approved
        donation = models.Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            comment='Hello',
            domain='PAYPAL',
            requestedvisibility='ANON',
            donor=anon_donor,
            event=self.event,
        )
        donation.approve_if_anonymous_and_no_comment(100)
        self.assertEqual(donation.readstate, 'PENDING')


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
            domainId='123456',
        )
        self.anonymous_donation = models.Donation.objects.create(
            event=self.event,
            amount=15,
            donor=self.anonymous_donor,
            transactionstate='COMPLETED',
            domainId='123457',
        )
        self.other_donation = models.Donation.objects.create(
            event=self.other_event,
            amount=25,
            donor=self.regular_donor,
            transactionstate='COMPLETED',
            domainId='123458',
        )

    def test_donation_list_no_event(self):
        resp = self.client.get(reverse('tracker:donationindex', args=('',)))
        self.assertContains(
            resp,
            '<small>Total (Count): $45.00 (3) &mdash; Max/Avg Donation: $25.00/$15.00</small>',
            html=True,
        )
        self.assertContains(resp, self.regular_donor.visible_name())
        self.assertContains(resp, f'<a href="{self.regular_donor.get_absolute_url()}">')
        self.assertContains(resp, self.anonymous_donor.visible_name())
        self.assertNotContains(resp, self.anonymous_donor.get_absolute_url())

    def test_donation_list_with_event(self):
        resp = self.client.get(reverse('tracker:donationindex', args=(self.event.id,)))
        self.assertContains(
            resp,
            '<small>Total (Count): $20.00 (2) &mdash; Max/Avg Donation: $15.00/$10.00</small>',
            html=True,
        )
        self.assertContains(resp, self.regular_donor.visible_name())
        self.assertContains(
            resp,
            f'<a href="{self.regular_donor.cache_for(self.event.id).get_absolute_url()}">',
        )
        self.assertContains(resp, self.anonymous_donor.visible_name())
        self.assertNotContains(
            resp, self.anonymous_donor.cache_for(self.event.id).get_absolute_url()
        )
