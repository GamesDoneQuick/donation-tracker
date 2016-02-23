import random
import pytz
from decimal import Decimal
from dateutil.parser import parse as parse_date

from django.test import TestCase, TransactionTestCase

import tracker.models as models
import tracker.viewutil as viewutil
import tracker.prizeutil as prizeutil
import tracker.randgen as randgen

class TestTicketPrizeDraws(TransactionTestCase):

    def setUp(self):
        self.eventStart = parse_date(
            "2012-01-01 01:00:00").replace(tzinfo=pytz.utc)
        self.rand = random.Random(998164)
        self.event = randgen.build_random_event(
            self.rand, self.eventStart, numDonors=100, numRuns=50)
        self.runsList = list(models.SpeedRun.objects.filter(event=self.event))
        self.donorList = list(models.Donor.objects.all())

    def test_draw_prize_with_tickets_no_donations(self):
        prize = randgen.generate_prize(
            self.rand, event=self.event, sumDonations=True, randomDraw=True, ticketDraw=True)
        prize.save()
        eligibleDonors = prize.eligible_donors()
        self.assertEqual(0, len(eligibleDonors))
        result, message = prizeutil.draw_prize(prize)
        self.assertFalse(result)
        self.assertEqual(None, prize.get_winner())

    def test_draw_prize_with_tickets(self):
        prize = randgen.generate_prize(
            self.rand, event=self.event, sumDonations=True, randomDraw=True, ticketDraw=True)
        prize.maximumbid = None
        prize.save()
        donor = self.donorList[0]
        donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=prize.minimumbid,
                                             maxAmount=prize.minimumbid, minTime=prize.start_draw_time(), maxTime=prize.end_draw_time())
        donation.save()
        models.PrizeTicket.objects.create(
            donation=donation, prize=prize, amount=donation.amount)
        eligibleDonors = prize.eligible_donors()
        self.assertEqual(1, len(eligibleDonors))
        self.assertEqual(eligibleDonors[0]['donor'], donor.id)
        result, message = prizeutil.draw_prize(prize)
        self.assertTrue(result)
        self.assertEqual(donor, prize.get_winner())

    def test_draw_prize_with_tickets_multiple_donors(self):
        prize = randgen.generate_prize(
            self.rand, event=self.event, sumDonations=True, randomDraw=True, ticketDraw=True)
        prize.maximumbid = None
        prize.save()
        donor = self.donorList[0]
        donation = randgen.generate_donation(self.rand, donor=donor, event=self.event, minAmount=prize.minimumbid,
                                             maxAmount=prize.minimumbid, minTime=prize.start_draw_time(), maxTime=prize.end_draw_time())
        donation.save()
        models.PrizeTicket.objects.create(
            donation=donation, prize=prize, amount=donation.amount)
        donor2 = self.donorList[1]
        donation2 = randgen.generate_donation(self.rand, donor=donor2, event=self.event, minAmount=prize.minimumbid,
                                              maxAmount=prize.minimumbid, minTime=prize.start_draw_time(), maxTime=prize.end_draw_time())
        donation2.save()
        eligibleDonors = prize.eligible_donors()
        self.assertEqual(1, len(eligibleDonors))
        self.assertEqual(eligibleDonors[0]['donor'], donor.id)
        self.assertAlmostEqual(
            eligibleDonors[0]['weight'], donation.amount / prize.minimumbid)
        result, message = prizeutil.draw_prize(prize)
        self.assertTrue(result)
        self.assertEqual(donor, prize.get_winner())

    def test_correct_prize_amount_with_split_tickets(self):
        prize0 = randgen.generate_prize(
            self.rand, event=self.event, sumDonations=True, randomDraw=True, ticketDraw=True)
        prize0.maximumbid = None
        prize0.save()
        prize1 = randgen.generate_prize(
            self.rand, event=self.event, sumDonations=True, randomDraw=True, ticketDraw=True)
        prize1.maximumbid = None
        prize1.save()
        donor = self.donorList[0]
        donation = randgen.generate_donation(
            self.rand, donor=donor, event=self.event, minAmount=prize0.minimumbid + prize1.minimumbid)
        donation.save()
        prize0Eligible = prize0.eligible_donors()
        self.assertEqual(0, len(prize0Eligible))
        prize1Eligible = prize1.eligible_donors()
        self.assertEqual(0, len(prize1Eligible))
        models.PrizeTicket.objects.create(
            donation=donation, prize=prize0, amount=donation.amount * Decimal('2.0'))
        models.PrizeTicket.objects.create(
            donation=donation, prize=prize1, amount=donation.amount * Decimal('2.0'))
        prize0Eligible = prize0.eligible_donors()
        self.assertEqual(1, len(prize0Eligible))
        prize1Eligible = prize1.eligible_donors()
        self.assertEqual(1, len(prize1Eligible))
        # TODO: more of these tests
