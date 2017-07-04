from tracker import models

from django.test import TransactionTestCase, RequestFactory
from django.contrib.auth.models import User, Permission
import tracker.views.api
import json
import datetime

class TestBid(TransactionTestCase):
    def setUp(self):
        self.event = models.Event.objects.create(
            date=datetime.date.today(), targetamount=5)
        self.run = models.SpeedRun.objects.create(
            name='Test Run', run_time='0:45:00', setup_time='0:05:00', order=1)
        self.donor = models.Donor.objects.create(
            firstname='John', lastname='Doe', email='johndoe@example.com')
        self.donation = models.Donation.objects.create(
            donor=self.donor, event=self.event, amount=5, transactionstate='COMPLETED')
        self.parent_bid = models.Bid.objects.create(
            name='Parent Test', speedrun=self.run)
        self.opened_bid = models.Bid.objects.create(
            name='Opened Test', istarget=True, parent=self.parent_bid, state='OPENED')
        self.closed_bid = models.Bid.objects.create(
            name='Closed Test', istarget=True, parent=self.parent_bid, state='CLOSED')
        self.hidden_bid = models.Bid.objects.create(
            name='Hidden Test', istarget=True, parent=self.parent_bid, state='HIDDEN')
        self.denied_bid = models.Bid.objects.create(
            name='Denied Test', istarget=True, parent=self.parent_bid, state='DENIED')
        self.pending_bid = models.Bid.objects.create(
            name='Pending Test', istarget=True, parent=self.parent_bid, state='PENDING')

    def test_opened_bid(self):
        models.DonationBid.objects.create(donation=self.donation, bid=self.opened_bid, amount=self.donation.amount)
        self.parent_bid.refresh_from_db()
        self.assertEqual(self.opened_bid.total, self.donation.amount, msg='opened bid total is wrong')
        self.assertEqual(self.parent_bid.total, self.donation.amount, msg='parent bid total is wrong')

    def test_closed_bid(self):
        models.DonationBid.objects.create(donation=self.donation, bid=self.closed_bid, amount=self.donation.amount)
        self.parent_bid.refresh_from_db()
        self.assertEqual(self.closed_bid.total, self.donation.amount, msg='closed bid total is wrong')
        self.assertEqual(self.parent_bid.total, self.donation.amount, msg='parent bid total is wrong')

    def test_hidden_bid(self):
        models.DonationBid.objects.create(donation=self.donation, bid=self.hidden_bid, amount=self.donation.amount)
        self.parent_bid.refresh_from_db()
        self.assertEqual(self.hidden_bid.total, self.donation.amount, msg='hidden bid total is wrong')
        self.assertEqual(self.parent_bid.total, 0, msg='parent bid total is wrong')

    def test_denied_bid(self):
        models.DonationBid.objects.create(donation=self.donation, bid=self.denied_bid, amount=self.donation.amount)
        self.parent_bid.refresh_from_db()
        self.assertEqual(self.denied_bid.total, self.donation.amount, msg='denied bid total is wrong')
        self.assertEqual(self.parent_bid.total, 0, msg='parent bid total is wrong')

    def test_pending_bid(self):
        models.DonationBid.objects.create(donation=self.donation, bid=self.pending_bid, amount=self.donation.amount)
        self.parent_bid.refresh_from_db()
        self.assertEqual(self.pending_bid.total, self.donation.amount, msg='pending bid total is wrong')
        self.assertEqual(self.parent_bid.total, 0, msg='parent bid total is wrong')
