import datetime

from django.db.models import ProtectedError
from django.test import TransactionTestCase

import tracker.models as models


class TestDeleteProtection(TransactionTestCase):
    def setUp(self):
        self.event = models.Event.objects.create(
            short='scratch',
            name='Scratch Event',
            datetime=datetime.datetime(2000, 1, 1, 12, tzinfo=datetime.timezone.utc),
        )

    def tearDown(self):
        for m in [
            models.PrizeWinner,
            models.DonationBid,
            models.Bid,
            models.Donation,
            models.Prize,
            models.Donor,
        ]:
            m.objects.all().delete()
        models.SpeedRun.objects.update(order=None)
        models.SpeedRun.objects.all().delete()

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
        return models.Prize.objects.get_or_create(
            name='Scratch Prize Timed',
            event=self.event,
            defaults=dict(
                starttime=datetime.datetime(
                    2000, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
                ),
                endtime=datetime.datetime(
                    2000, 1, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
                ),
            ),
        )[0]

    @property
    def scratchPrizeRun(self):
        return models.Prize.objects.get_or_create(
            name='Scratch Prize Run',
            event=self.event,
            defaults=dict(startrun=self.scratchRun, endrun=self.scratchRun),
        )[0]

    @property
    def scratchPrizeWinner(self):
        return models.PrizeWinner.objects.get_or_create(
            winner=self.scratchDonor, prize=self.scratchPrizeTimed
        )[0]

    @property
    def scratchDonor(self):
        return models.Donor.objects.get_or_create(email='scratch_donor@example.com')[0]

    @property
    def scratchDonation(self):
        return models.Donation.objects.get_or_create(
            defaults=dict(domain='PAYPAL', event=self.event, amount=5),
        )[0]

    @property
    def scratchDonationWithDonor(self):
        return models.Donation.objects.get_or_create(
            defaults=dict(
                domain='PAYPAL',
                event=self.event,
                donor=self.scratchDonor,
                amount=5,
                transactionstate='COMPLETED',
            ),
        )[0]

    @property
    def scratchDonationBid(self):
        return models.DonationBid.objects.get_or_create(
            donation=self.scratchDonation, bid=self.scratchBidRun, amount=5
        )[0]

    @property
    def scratchRun(self):
        return models.SpeedRun.objects.get_or_create(
            name='Scratch Run',
            event=self.event,
            defaults=dict(
                order=1,
                run_time='0:10:00',
            ),
        )[0]

    @property
    def scratchBidEvent(self):
        return models.Bid.objects.get_or_create(name='Scratch Bid', event=self.event)[0]

    @property
    def scratchBidRun(self):
        return models.Bid.objects.get_or_create(
            name='Scratch Bid', speedrun=self.scratchRun, istarget=True
        )[0]

    def testDeleteEvent(self):
        self.assertDeleteProtected(self.event, self.scratchBidEvent)
        self.assertDeleteProtected(self.event, self.scratchRun)
        self.assertDeleteProtected(self.event, self.scratchPrizeTimed)
        self.assertDeleteProtected(self.event, self.scratchDonation)
        with self.Delete(
            models.Event.objects.create(
                short='delete',
                name='Delete Event',
                datetime=datetime.datetime(2001, 1, 1, 12),
            )
        ):
            pass

    def testDeleteRun(self):
        with self.Delete(self.scratchRun) as run:
            self.assertDeleteProtected(run, self.scratchPrizeRun)
            self.assertDeleteProtected(run, self.scratchBidRun)

    def testDeleteDonor(self):
        with self.Delete(self.scratchDonor) as donor:
            self.assertDeleteProtected(donor, self.scratchPrizeWinner)
            self.assertDeleteProtected(donor, self.scratchDonationWithDonor)

    def testDeleteDonation(self):
        with self.Delete(self.scratchDonation) as donation:
            self.assertDeleteProtected(donation, self.scratchDonationBid)
