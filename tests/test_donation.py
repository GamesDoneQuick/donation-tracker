# coding: utf-8

import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from tracker.models import Donation, Donor, Event


class TestDonation(TestCase):
    def setUp(self):
        self.event = Event(
            receivername="Médecins Sans Frontières",
            targetamount=1,
            paypalemail="msf@example.com",
            paypalcurrency="USD",
            datetime=datetime.datetime(2018, 1, 1),
        )

    def test_anonymous(self):
        # Anonymous donation is anonymous
        donation = Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            domain="PAYPAL",
            requestedvisibility="ANON",
            event=self.event,
        )
        self.assertTrue(donation.anonymous())

        # Donation from an anonymous donor with CURR is anonymous
        donation = Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            domain="PAYPAL",
            requestedvisibility="CURR",
            donor=Donor(visibility="ANON"),
            event=self.event,
        )
        self.assertTrue(donation.anonymous())

        # Donation from a non-anonymous donor with CURR is not anonymous
        donation = Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            domain="PAYPAL",
            requestedvisibility="CURR",
            donor=Donor(visibility="ALIAS"),
            event=self.event,
        )
        self.assertFalse(donation.anonymous())

    def test_anonymous_and_no_comment(self):
        alias_donor = Donor(visibility="ALIAS")
        anon_donor = Donor(visibility="ANON")

        # GOOD: Anonymous donation with no comment and any donor
        donation = Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            domain="PAYPAL",
            requestedvisibility="ANON",
            donor=alias_donor,
            event=self.event,
        )
        self.assertTrue(donation.anonymous_and_no_comment())

        # GOOD: Donation with no comment, CURR visibility, and anonymous donor
        donation = Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            domain="PAYPAL",
            requestedvisibility="CURR",
            donor=anon_donor,
            event=self.event,
        )
        self.assertTrue(donation.anonymous_and_no_comment())

        # BAD: Donation with no comment, but some non-anonymous visibility
        donation = Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            domain="PAYPAL",
            requestedvisibility="ALIAS",
            donor=anon_donor,
            event=self.event,
        )
        self.assertFalse(donation.anonymous_and_no_comment())
        donation.approve_if_anonymous_and_no_comment()
        self.assertEqual(donation.readstate, "PENDING")

        # BAD: Donation with a comment
        donation = Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            comment="Hello",
            domain="PAYPAL",
            requestedvisibility="ANON",
            donor=anon_donor,
            event=self.event,
        )
        self.assertEqual(donation.readstate, "PENDING")

    def test_approve_if_anonymous_and_no_comment(self):
        alias_donor = Donor(visibility="ALIAS")
        anon_donor = Donor(visibility="ANON")

        # If the comment was already read (or anything not pending), don't act
        donation = Donation(
            timereceived=timezone.now(),
            readstate="READ",
            amount=Decimal(1.5),
            domain="PAYPAL",
            requestedvisibility="ANON",
            donor=alias_donor,
            event=self.event,
        )
        donation.approve_if_anonymous_and_no_comment()
        self.assertEqual(donation.readstate, "READ")

        # With no threshold given, just ignore
        donation = Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            domain="PAYPAL",
            requestedvisibility="ANON",
            donor=alias_donor,
            event=self.event,
        )
        donation.approve_if_anonymous_and_no_comment()
        self.assertEqual(donation.readstate, "IGNORED")

        # With a threshold and a donation above it, send to reader
        donation = Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            domain="PAYPAL",
            requestedvisibility="CURR",
            donor=anon_donor,
            event=self.event,
        )
        donation.approve_if_anonymous_and_no_comment(1)
        self.assertEqual(donation.readstate, "READY")

        # With a threshold and a donation below it, ignore
        donation = Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            domain="PAYPAL",
            requestedvisibility="ANON",
            donor=anon_donor,
            event=self.event,
        )
        donation.approve_if_anonymous_and_no_comment(5)
        self.assertEqual(donation.readstate, "IGNORED")

        # Donation with a comment should not be approved
        donation = Donation(
            timereceived=timezone.now(),
            amount=Decimal(1.5),
            comment="Hello",
            domain="PAYPAL",
            requestedvisibility="ANON",
            donor=anon_donor,
            event=self.event,
        )
        donation.approve_if_anonymous_and_no_comment(100)
        self.assertEqual(donation.readstate, "PENDING")
