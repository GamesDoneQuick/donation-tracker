import datetime
from decimal import Decimal

from django.test import TransactionTestCase

from .. import models

noon = datetime.time(12, 0)
today = datetime.date.today()
today_noon = datetime.datetime.combine(today, noon)
tomorrow = today + datetime.timedelta(days=1)
tomorrow_noon = datetime.datetime.combine(tomorrow, noon)
long_ago = today - datetime.timedelta(days=180)
long_ago_noon = datetime.datetime.combine(long_ago, noon)


class TestWordFilter(TransactionTestCase):
    def setUp(self):
        self.filter = models.WordFilter.objects.create(word='hype')
        self.event = models.Event.objects.create(
            short='ev1', name='Event 1', targetamount=5, datetime=today_noon)

    def testRejectionOfWordMatch(self):
        donation = models.Donation.objects.create(event=self.event, comment='HYPE', amount=5)
        self.assertEqual(donation.commentstate, 'DENIED')
        self.assertEqual(donation.readstate, 'IGNORED')
        self.assertTrue('DENIED due to matching filter word' in donation.modcomment)

    def testNoRejectionForPartialWordMatch(self):
        donation = models.Donation.objects.create(event=self.event, comment='HYPED', amount=5)
        self.assertNotEqual(donation.commentstate, 'DENIED')
        self.assertNotEqual(donation.readstate, 'IGNORED')
        self.assertFalse('DENIED due to matching filter word' in donation.modcomment)

    def testNoRejectionForNoMatch(self):
        donation = models.Donation.objects.create(event=self.event, comment='relaxed', amount=5)
        self.assertNotEqual(donation.commentstate, 'DENIED')
        self.assertNotEqual(donation.readstate, 'IGNORED')
        self.assertFalse('DENIED due to matching filter word' in donation.modcomment)

    def testNoRejectionOfExistingDonations(self):
        donation = models.Donation.objects.create(event=self.event, comment='relaxed', amount=5)
        donation.comment = 'HYPE'
        donation.save()
        self.assertNotEqual(donation.commentstate, 'DENIED')
        self.assertNotEqual(donation.readstate, 'IGNORED')


class TestAmountFilter(TransactionTestCase):
    def setUp(self):
        self.filter = models.AmountFilter.objects.create(amount=Decimal('4.20'))
        self.event = models.Event.objects.create(
            short='ev1', name='Event 1', targetamount=5, datetime=today_noon)

    def testRejectionOfAmountMatch(self):
        donation = models.Donation.objects.create(event=self.event, comment='HYPE', amount=Decimal('4.20'))
        self.assertEqual(donation.commentstate, 'DENIED')
        self.assertEqual(donation.readstate, 'IGNORED')
        self.assertTrue('DENIED due to matching filter amount' in donation.modcomment)

    def testNoRejectionOfUnmatchedAmount(self):
        donation = models.Donation.objects.create(event=self.event, comment='HYPE', amount=5)
        self.assertNotEqual(donation.commentstate, 'DENIED')
        self.assertNotEqual(donation.readstate, 'IGNORED')
        self.assertFalse('DENIED due to matching filter amount' in donation.modcomment)

    def testNoRejectionOfExistingDonations(self):
        donation = models.Donation.objects.create(event=self.event, comment='HYPE', amount=5)
        donation.amount = Decimal('4.20')
        donation.save()
        self.assertNotEqual(donation.commentstate, 'DENIED')
        self.assertNotEqual(donation.readstate, 'IGNORED')
