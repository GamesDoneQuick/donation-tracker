import tracker.models as models

from django.test import TransactionTestCase
from django.db.models import ProtectedError

import datetime
import pytz


class TestDeleteProtection(TransactionTestCase):
    def setUp(self):
        self.event = models.Event.objects.create(
            short='scratch',
            name='Scratch Event',
            datetime=datetime.datetime(2000, 1, 1, 12, tzinfo=pytz.utc),
            targetamount=1000,
        )

    def tearDown(self):
        for m in [
            models.PrizeWinner,
            models.DonationBid,
            models.Bid,
            models.Donation,
            models.Prize,
            models.Donor,
            models.SpeedRun,
        ]:
            m.objects.all().delete()

    def assertDeleteProtected(self, deleted, protected):  # noqa N806
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
    def scratch_prize_timed(self):
        return models.Prize.objects.get_or_create(
            name='Scratch Prize Timed',
            event=self.event,
            defaults=dict(
                starttime=datetime.datetime(2000, 1, 1, 0, 0, 0, tzinfo=pytz.utc),
                endtime=datetime.datetime(2000, 1, 1, 1, 0, 0, tzinfo=pytz.utc),
            ),
        )[0]

    @property
    def scratch_prize_run(self):
        return models.Prize.objects.get_or_create(
            name='Scratch Prize Run',
            event=self.event,
            defaults=dict(startrun=self.scratch_run, endrun=self.scratch_run),
        )[0]

    @property
    def scratch_prize_winner(self):
        return models.PrizeWinner.objects.get_or_create(
            winner=self.scratch_donor, prize=self.scratch_prize_timed
        )[0]

    @property
    def scratch_donor(self):
        return models.Donor.objects.get_or_create(email='scratch_donor@example.com')[0]

    @property
    def scratch_donation(self):
        return models.Donation.objects.get_or_create(
            domainId='scratch',
            defaults=dict(domain='PAYPAL', event=self.event, amount=5),
        )[0]

    @property
    def scratch_donation_with_donor(self):
        return models.Donation.objects.get_or_create(
            domainId='scratch_donor',
            defaults=dict(
                domain='PAYPAL',
                event=self.event,
                donor=self.scratch_donor,
                amount=5,
                transactionstate='COMPLETED',
            ),
        )[0]

    @property
    def scratch_donation_bid(self):
        return models.DonationBid.objects.get_or_create(
            donation=self.scratch_donation, bid=self.scratch_bid_run, amount=5
        )[0]

    @property
    def scratch_run(self):
        return models.SpeedRun.objects.get_or_create(
            name='Scratch Run',
            event=self.event,
            defaults=dict(
                starttime=datetime.datetime(2000, 1, 1, 0, 0, 0, tzinfo=pytz.utc),
                endtime=datetime.datetime(2000, 1, 1, 1, 0, 0, tzinfo=pytz.utc),
            ),
        )[0]

    @property
    def scratch_bid_event(self):
        return models.Bid.objects.get_or_create(name='Scratch Bid', event=self.event)[0]

    @property
    def scratch_bid_run(self):
        return models.Bid.objects.get_or_create(
            name='Scratch Bid', speedrun=self.scratch_run, istarget=True
        )[0]

    def test_delete_event(self):
        self.assertDeleteProtected(self.event, self.scratch_bid_event)
        self.assertDeleteProtected(self.event, self.scratch_run)
        self.assertDeleteProtected(self.event, self.scratch_prize_timed)
        self.assertDeleteProtected(self.event, self.scratch_donation)
        with self.Delete(
            models.Event.objects.create(
                short='delete',
                name='Delete Event',
                datetime=datetime.datetime(2001, 1, 1, 12),
                targetamount=1000,
            )
        ):
            pass

    def test_delete_run(self):
        with self.Delete(self.scratch_run) as run:
            self.assertDeleteProtected(run, self.scratch_prize_run)
            self.assertDeleteProtected(run, self.scratch_bid_run)

    def test_delete_donor(self):
        with self.Delete(self.scratch_donor) as donor:
            self.assertDeleteProtected(donor, self.scratch_prize_winner)
            self.assertDeleteProtected(donor, self.scratch_donation_with_donor)

    def test_delete_donation(self):
        with self.Delete(self.scratch_donation) as donation:
            self.assertDeleteProtected(donation, self.scratch_donation_bid)
