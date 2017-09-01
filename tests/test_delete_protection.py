import tracker.models as models

from django.test import TestCase, TransactionTestCase
from django.db.models import ProtectedError

import datetime
import pytz


class TestDeleteProtection(TransactionTestCase):

    def setUp(self):
        self.event = models.Event.objects.create(
            short='scratch', name='Scratch Event', date=datetime.date(2000, 1, 1), targetamount=1000)

    def tearDown(self):
        for m in [models.PrizeWinner, models.PrizeTicket, models.DonationBid, models.Bid,
                  models.Donation, models.Prize, models.Donor, models.SpeedRun]:
            m.objects.all().delete()

    def assertDeleteProtected(self, deleted, protected):
        protected.clean()
        with self.assertRaises(ProtectedError):
            deleted.delete()
        protected.delete()

    class Delete:

        def __init__(self, obj):
            self.obj = obj
            assert hasattr(self.obj, 'clean')
            assert hasattr(self.obj, 'delete')

        def __enter__(self):
            self.obj.clean()
            return self.obj

        def __exit__(self, exc_type, exc_val, exc_tb):
            if not exc_tb:
                self.obj.delete()

    @property
    def scratchPrizeTimed(self):
        return models.Prize.objects.get_or_create(name='Scratch Prize Timed', event=self.event,
                                                  defaults=dict(
                                                      starttime=datetime.datetime(
                                                          2000, 1, 1, 0, 0, 0, tzinfo=pytz.utc),
                                                      endtime=datetime.datetime(2000, 1, 1, 1, 0, 0, tzinfo=pytz.utc)))[0]

    @property
    def scratchPrizeTicketed(self):
        return models.Prize.objects.get_or_create(name='Scratch Prize Ticketed', event=self.event,
                                                  defaults=dict(ticketdraw=True))[0]

    @property
    def scratchPrizeRun(self):
        return models.Prize.objects.get_or_create(name='Scratch Prize Run', event=self.event,
                                                  defaults=dict(
                                                      startrun=self.scratchRun, endrun=self.scratchRun))[0]

    @property
    def scratchPrizeWinner(self):
        return models.PrizeWinner.objects.get_or_create(winner=self.scratchDonor, prize=self.scratchPrizeTimed)[0]

    @property
    def scratchPrizeWinnerTicketed(self):
        return models.PrizeWinner.objects.get_or_create(winner=self.scratchDonor, prize=self.scratchPrizeTicketed)[0]

    @property
    def scratchPrizeTicket(self):
        return models.PrizeTicket.objects.get_or_create(prize=self.scratchPrizeTicketed, donation=self.scratchDonation,
                                                        defaults=dict(amount=5))[0]

    @property
    def scratchDonor(self):
        return models.Donor.objects.get_or_create(email='scratch_donor@example.com')[0]

    @property
    def scratchDonation(self):
        return models.Donation.objects.get_or_create(domainId='scratch',
                                                     defaults=dict(
                                                         domain='PAYPAL', event=self.event, amount=5))[0]

    @property
    def scratchDonationWithDonor(self):
        return models.Donation.objects.get_or_create(domainId='scratchDonor',
                                                     defaults=dict(
                                                         domain='PAYPAL', event=self.event, donor=self.scratchDonor,
                                                         amount=5, transactionstate='COMPLETED'))[0]

    @property
    def scratchDonationBid(self):
        return models.DonationBid.objects.get_or_create(donation=self.scratchDonation, bid=self.scratchBidRun, amount=5)[0]

    @property
    def scratchRun(self):
        return models.SpeedRun.objects.get_or_create(name='Scratch Run', event=self.event,
                                                     defaults=dict(
                                                         starttime=datetime.datetime(
                                                             2000, 1, 1, 0, 0, 0, tzinfo=pytz.utc),
                                                         endtime=datetime.datetime(2000, 1, 1, 1, 0, 0, tzinfo=pytz.utc)))[0]

    @property
    def scratchBidEvent(self):
        return models.Bid.objects.get_or_create(name='Scratch Bid', event=self.event)[0]

    @property
    def scratchBidRun(self):
        return models.Bid.objects.get_or_create(name='Scratch Bid', speedrun=self.scratchRun, istarget=True)[0]

    def testDeleteEvent(self):
        self.assertDeleteProtected(self.event, self.scratchBidEvent)
        self.assertDeleteProtected(self.event, self.scratchRun)
        self.assertDeleteProtected(self.event, self.scratchPrizeTimed)
        self.assertDeleteProtected(self.event, self.scratchDonation)
        with self.Delete(models.Event.objects.create(short='delete', name='Delete Event',
                                                     date=datetime.date(2001, 1, 1), targetamount=1000)):
            pass

    def testDeleteRun(self):
        with self.Delete(self.scratchRun) as run:
            self.assertDeleteProtected(run, self.scratchPrizeRun)
            self.assertDeleteProtected(run, self.scratchBidRun)

    def testDeletePrize(self):
        with self.Delete(self.scratchPrizeTicketed) as prize:
            self.assertDeleteProtected(prize, self.scratchPrizeWinnerTicketed)
            self.assertDeleteProtected(prize, self.scratchPrizeTicket)

    def testDeleteDonor(self):
        with self.Delete(self.scratchDonor) as donor:
            self.assertDeleteProtected(donor, self.scratchPrizeWinner)
            self.assertDeleteProtected(donor, self.scratchDonationWithDonor)

    def testDeleteDonation(self):
        with self.Delete(self.scratchDonation) as donation:
            self.assertDeleteProtected(donation, self.scratchDonationBid)
            self.assertDeleteProtected(donation, self.scratchPrizeTicket)
