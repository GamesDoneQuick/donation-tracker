import datetime
import operator
import random
from collections import defaultdict
from decimal import Decimal
from functools import reduce
from unittest.mock import patch

import post_office.models
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.models import Permission, User
from django.contrib.sites.models import Site
from django.core.exceptions import (
    ImproperlyConfigured,
    ObjectDoesNotExist,
    ValidationError,
)
from django.db.models import Sum
from django.test import RequestFactory, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils.formats import localize

from tracker import models, prizeutil, settings, util
from tracker.util import anywhere_on_earth_tz

from . import randgen
from .util import (
    AssertionHelpers,
    MigrationsTestCase,
    create_test_template,
    long_ago_noon,
    parse_test_mail,
    today_noon,
    tomorrow_noon,
)


class TestPrize(TransactionTestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand, start_time=today_noon)
        self.event.save()
        self.prize = randgen.generate_prize(self.rand, event=self.event, maxwinners=2)
        self.prize.save()
        self.donor = randgen.generate_donor(self.rand)
        self.donor.save()
        self.other_donor = randgen.generate_donor(self.rand)
        self.other_donor.save()

    def test_lifecycle_annotations(self):
        prize = models.Prize.objects.time_annotation().claim_annotations().first()
        self.assertEqual(prize, self.prize)
        self.assertEqual(prize.winner_email_pending, 0)
        self.assertEqual(prize.accept_count, 0)
        self.assertEqual(prize.pending_count, 0)
        self.assertEqual(prize.expired_count, 0)
        self.assertEqual(prize.decline_count, 0)
        self.assertEqual(prize.accept_email_sent_count, 0)
        self.assertFalse(prize.accept_email_pending)
        self.assertEqual(prize.needs_shipping, 0)
        self.assertEqual(prize.shipped_email_pending, 0)
        self.assertEqual(prize.lifecycle, 'notify_contributor')
        prize.acceptemailsent = True
        prize.endtime = tomorrow_noon
        prize.save()
        prize = models.Prize.objects.time_annotation().claim_annotations().first()
        self.assertEqual(prize.lifecycle, 'accepted')
        prize.endtime = None
        prize.save()
        prize = models.Prize.objects.time_annotation().claim_annotations().first()
        self.assertEqual(prize.lifecycle, 'ready')
        prize_claim = models.PrizeClaim.objects.create(prize=prize, winner=self.donor)
        prize = models.Prize.objects.time_annotation().claim_annotations().first()
        self.assertEqual(prize.winner_email_pending, 1)
        self.assertEqual(prize.accept_count, 0)
        self.assertEqual(prize.pending_count, 1)
        self.assertEqual(prize.expired_count, 0)
        self.assertEqual(prize.decline_count, 0)
        self.assertEqual(
            prize.lifecycle, 'ready'
        )  # because there's still another claim available
        prize_claim.acceptdeadline = tomorrow_noon
        prize_claim.save()
        prize = models.Prize.objects.time_annotation().claim_annotations().first()
        self.assertEqual(prize.pending_count, 1)
        self.assertEqual(prize.expired_count, 0)
        self.assertEqual(prize.decline_count, 0)
        prize = (
            models.Prize.objects.time_annotation()
            .claim_annotations(tomorrow_noon)
            .first()
        )
        self.assertEqual(prize.pending_count, 0)
        self.assertEqual(prize.expired_count, 1)
        self.assertEqual(prize.decline_count, 0)
        prize_claim.winneremailsent = True
        prize_claim.save()
        prize = models.Prize.objects.time_annotation().claim_annotations().first()
        self.assertEqual(prize.winner_email_pending, 0)
        other_prize_claim = models.PrizeClaim.objects.create(
            prize=self.prize, winner=self.other_donor
        )
        prize = models.Prize.objects.time_annotation().claim_annotations().first()
        self.assertEqual(prize.winner_email_pending, 1)
        self.assertEqual(prize.pending_count, 2)
        self.assertEqual(prize.lifecycle, 'drawn')
        prize_claim.acceptcount = 1
        prize_claim.pendingcount = 0
        prize_claim.save()
        other_prize_claim.winneremailsent = True
        other_prize_claim.pendingcount = 0
        other_prize_claim.declinecount = 1
        other_prize_claim.save()
        prize = models.Prize.objects.time_annotation().claim_annotations().first()
        self.assertFalse(prize.winner_email_pending)
        self.assertEqual(prize.accept_count, 1)
        self.assertEqual(prize.pending_count, 0)
        self.assertEqual(prize.decline_count, 1)
        self.assertEqual(prize.accept_email_sent_count, 0)
        self.assertTrue(prize.accept_email_pending)
        self.assertEqual(prize.needs_shipping, 0)
        self.assertEqual(prize.lifecycle, 'ready')  # because there's a declined claim
        prize_claim.acceptemailsentcount = 1
        prize_claim.save()
        other_prize_claim.acceptemailsentcount = 0
        other_prize_claim.acceptcount = 1
        other_prize_claim.declinecount = 0
        other_prize_claim.save()
        prize = models.Prize.objects.time_annotation().claim_annotations().first()
        self.assertEqual(prize.accept_email_sent_count, 1)
        self.assertTrue(prize.accept_email_pending)
        self.assertEqual(prize.needs_shipping, 1)
        self.assertEqual(prize.shipped_email_pending, 0)
        self.assertEqual(prize.lifecycle, 'claimed')
        other_prize_claim.acceptemailsentcount = 1
        other_prize_claim.save()
        prize = models.Prize.objects.time_annotation().claim_annotations().first()

        self.assertEqual(prize.accept_email_sent_count, 2)
        self.assertFalse(prize.accept_email_pending)
        self.assertEqual(prize.needs_shipping, 2)
        self.assertEqual(prize.shipped_email_pending, 0)
        self.assertEqual(prize.lifecycle, 'needs_shipping')
        prize_claim.shippingstate = 'SHIPPED'
        prize_claim.save()
        prize = models.Prize.objects.time_annotation().claim_annotations().first()
        self.assertEqual(prize.needs_shipping, 1)
        self.assertEqual(prize.shipped_email_pending, 1)
        self.assertEqual(prize.lifecycle, 'needs_shipping')
        other_prize_claim.shippingstate = 'SHIPPED'
        other_prize_claim.save()
        prize = models.Prize.objects.time_annotation().claim_annotations().first()
        self.assertEqual(prize.needs_shipping, 0)
        self.assertEqual(prize.shipped_email_pending, 2)
        self.assertEqual(prize.lifecycle, 'shipped')
        prize_claim.shippingemailsent = True
        prize_claim.save()
        prize = models.Prize.objects.time_annotation().claim_annotations().first()
        self.assertEqual(prize.shipped_email_pending, 1)
        self.assertEqual(prize.lifecycle, 'shipped')
        other_prize_claim.shippingemailsent = True
        other_prize_claim.save()
        prize = models.Prize.objects.time_annotation().claim_annotations().first()
        self.assertEqual(prize.shipped_email_pending, 0)
        self.assertEqual(prize.lifecycle, 'completed')


class TestPrizeGameRange(TransactionTestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand, start_time=today_noon)
        self.event.save()

    def test_time_prize_no_range(self):
        runs = randgen.generate_runs(self.rand, self.event, 7, ordered=True)
        eventEnd = runs[-1].endtime
        timeA = randgen.random_time(self.rand, self.event.datetime, eventEnd)
        timeB = randgen.random_time(self.rand, self.event.datetime, eventEnd)
        randomStart = min(timeA, timeB)
        randomEnd = max(timeA, timeB)
        prize = randgen.generate_prize(
            self.rand, event=self.event, start_time=randomStart, end_time=randomEnd
        )
        self.assertEqual(randomStart, prize.start_draw_time())
        self.assertEqual(randomEnd, prize.end_draw_time())


class TestPrizeDrawingGeneratedEvent(TransactionTestCase):
    def setUp(self):
        self.eventStart = util.parse_time('2014-01-01 16:00:00Z')
        self.rand = random.Random(516273)
        self.event = randgen.build_random_event(
            self.rand, start_time=self.eventStart, num_donors=100, num_runs=50
        )
        self.runsList = list(models.SpeedRun.objects.filter(event=self.event))
        self.donorList = list(models.Donor.objects.all())

    def test_draw_random_prize_no_donations(self):
        prizeList = randgen.generate_prizes(
            self.rand, self.event, 50, list_of_runs=self.runsList
        )
        for prize in prizeList:
            for randomness in [True, False]:
                for useSum in [True, False]:
                    prize.randomdraw = randomness
                    prize.sumdonations = useSum
                    prize.save()
                    eligibleDonors = prize.eligible_donors()
                    self.assertEqual(0, len(eligibleDonors))
                    result, message = prizeutil.draw_prize(prize)
                    self.assertFalse(result)
                    self.assertEqual(0, prize.current_win_count())

    def test_draw_prize_one_donor(self):
        startRun = self.runsList[14]
        endRun = self.runsList[28]
        for useRandom in [True, False]:
            for useSum in [True, False]:
                for donationSize in ['above', 'equal', 'below']:
                    prize = randgen.generate_prize(
                        self.rand,
                        event=self.event,
                        sum_donations=useSum,
                        random_draw=useRandom,
                        start_run=startRun,
                        end_run=endRun,
                    )
                    prize.save()
                    donor = self.rand.choice(self.donorList)
                    donation = randgen.generate_donation(
                        self.rand,
                        donor=donor,
                        event=self.event,
                        min_time=prize.start_draw_time(),
                        max_time=prize.end_draw_time(),
                    )
                    if donationSize == 'above':
                        donation.amount = prize.minimumbid + Decimal('5.00')
                    elif donationSize == 'equal':
                        donation.amount = prize.minimumbid
                    elif donationSize == 'below':
                        donation.amount = max(
                            Decimal('0.00'), prize.minimumbid - Decimal('5.00')
                        )
                    donation.save()
                    eligibleDonors = prize.eligible_donors()
                    if donationSize == 'below' and prize.randomdraw:
                        self.assertEqual(0, len(eligibleDonors))
                    else:
                        self.assertEqual(1, len(eligibleDonors))
                        self.assertEqual({donor}, set(eligibleDonors))
                        self.assertEqual(donation.amount, eligibleDonors[donor])
                    result, message = prizeutil.draw_prize(prize)
                    if donationSize != 'below' or not prize.randomdraw:
                        self.assertTrue(result)
                        self.assertEqual([donor], prize.get_winners())
                    else:
                        self.assertFalse(result)
                        self.assertEqual([], prize.get_winners())
                    donation.delete()
                    prize.claims.all().delete()
                    prize.delete()

    def test_draw_prize_multiple_donors_random_nosum(self):
        startRun = self.runsList[28]
        endRun = self.runsList[30]
        prize = randgen.generate_prize(
            self.rand,
            event=self.event,
            sum_donations=False,
            random_draw=True,
            start_run=startRun,
            end_run=endRun,
        )
        prize.save()
        donationDonors = set()
        for donor in self.donorList:
            if self.rand.getrandbits(1) == 0:
                donation = randgen.generate_donation(
                    self.rand,
                    donor=donor,
                    event=self.event,
                    min_amount=prize.minimumbid,
                    max_amount=prize.minimumbid + Decimal('100.00'),
                    min_time=prize.start_draw_time(),
                    max_time=prize.end_draw_time(),
                )
                donation.save()
                donationDonors.add(donor)
            # Add a few red herrings to make sure out of range donations aren't
            # used
            donation2 = randgen.generate_donation(
                self.rand,
                donor=donor,
                event=self.event,
                min_amount=prize.minimumbid,
                max_amount=prize.minimumbid + Decimal('100.00'),
                max_time=prize.start_draw_time() - datetime.timedelta(seconds=1),
            )
            donation2.save()
            donation3 = randgen.generate_donation(
                self.rand,
                donor=donor,
                event=self.event,
                min_amount=prize.minimumbid,
                max_amount=prize.minimumbid + Decimal('100.00'),
                min_time=prize.end_draw_time() + datetime.timedelta(seconds=1),
            )
            donation3.save()
        eligibleDonors = prize.eligible_donors()
        self.assertEqual(set(donationDonors), set(eligibleDonors))
        for donor, amount in eligibleDonors.items():
            donation = donor.donation_set.filter(
                timereceived__gte=prize.start_draw_time(),
                timereceived__lte=prize.end_draw_time(),
            )[0]
            self.assertEqual(donation.amount, amount)
        winners = []
        # magic seeds to verify randomness
        for seed in [0, 1, 5]:
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertIn(prize.get_winners()[0], donationDonors)
            winners.append(prize.get_winners()[0])
            current = prize.get_winners()[0]
            prize.claims.all().delete()
            prize.save()
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertEqual(current, prize.get_winners()[0])
            prize.claims.all().delete()
            prize.save()
        self.assertEqual(
            len(set(winners)), 3, 'Winners were not unique (randomness failure?)'
        )

    def test_draw_prize_multiple_donors_random_sum(self):
        startRun = self.runsList[41]
        endRun = self.runsList[46]
        prize = randgen.generate_prize(
            self.rand,
            event=self.event,
            sum_donations=True,
            random_draw=True,
            start_run=startRun,
            end_run=endRun,
        )
        prize.save()
        donationDonors = defaultdict(lambda: Decimal('0.00'))
        for donor in self.donorList:
            numDonations = self.rand.getrandbits(4)
            redHerrings = self.rand.getrandbits(4)
            for i in range(0, numDonations):
                donation = randgen.generate_donation(
                    self.rand,
                    donor=donor,
                    event=self.event,
                    min_amount=Decimal('0.01'),
                    max_amount=prize.minimumbid - Decimal('0.10'),
                    min_time=prize.start_draw_time(),
                    max_time=prize.end_draw_time(),
                )
                donation.save()
                donationDonors[donor] += donation.amount
            # toss in a few extras to keep the drawer on its toes
            for i in range(0, redHerrings):
                if self.rand.getrandbits(1) == 0:
                    donation = randgen.generate_donation(
                        self.rand,
                        donor=donor,
                        event=self.event,
                        min_amount=Decimal('0.01'),
                        max_amount=prize.minimumbid - Decimal('0.10'),
                        max_time=prize.start_draw_time()
                        - datetime.timedelta(seconds=1),
                    )
                else:
                    donation = randgen.generate_donation(
                        self.rand,
                        donor=donor,
                        event=self.event,
                        min_amount=Decimal('0.01'),
                        max_amount=prize.minimumbid - Decimal('0.10'),
                        min_time=prize.end_draw_time() + datetime.timedelta(seconds=1),
                    )
                donation.save()
        donationDonors = {
            d: a for d, a in donationDonors.items() if a >= prize.minimumbid
        }
        eligibleDonors = prize.eligible_donors()
        self.assertEqual(set(donationDonors), set(eligibleDonors))
        for donor in eligibleDonors:
            amount = donationDonors[donor]
            donations = donor.donation_set.filter(
                timereceived__gte=prize.start_draw_time(),
                timereceived__lte=prize.end_draw_time(),
            )
            amount_sum = donations.aggregate(Sum('amount'))['amount__sum']
            self.assertEqual(amount, amount_sum)
        winners = []
        # magic seeds for uniqueness
        for seed in [51234, 235426, 62363245]:
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertIn(prize.get_winners()[0], donationDonors)
            winners.append(prize.get_winners()[0])
            current = prize.get_winners()
            prize.claims.all().delete()
            prize.save()
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertEqual(current, prize.get_winners())
            prize.claims.all().delete()
            prize.save()
        self.assertEqual(len(winners), len(set(winners)), msg='Not unique')

    def test_draw_prize_multiple_donors_norandom_nosum(self):
        startRun = self.runsList[25]
        endRun = self.runsList[34]
        prize = randgen.generate_prize(
            self.rand,
            event=self.event,
            sum_donations=False,
            random_draw=False,
            start_run=startRun,
            end_run=endRun,
        )
        prize.save()
        largestDonor = None
        largestAmount = Decimal('0.00')
        for donor in self.donorList:
            numDonations = self.rand.getrandbits(4)
            redHerrings = self.rand.getrandbits(4)
            for i in range(0, numDonations):
                donation = randgen.generate_donation(
                    self.rand,
                    donor=donor,
                    event=self.event,
                    min_amount=Decimal('0.01'),
                    max_amount=Decimal('1000.00'),
                    min_time=prize.start_draw_time(),
                    max_time=prize.end_draw_time(),
                )
                donation.save()
                if donation.amount > largestAmount:
                    largestDonor = donor
                    largestAmount = donation.amount
            # toss in a few extras to keep the drawer on its toes
            for i in range(0, redHerrings):
                if self.rand.getrandbits(1) == 0:
                    donation = randgen.generate_donation(
                        self.rand,
                        donor=donor,
                        event=self.event,
                        min_amount=Decimal('1000.01'),
                        max_amount=Decimal('2000.00'),
                        max_time=prize.start_draw_time()
                        - datetime.timedelta(seconds=1),
                    )
                else:
                    donation = randgen.generate_donation(
                        self.rand,
                        donor=donor,
                        event=self.event,
                        min_amount=Decimal('1000.01'),
                        max_amount=max(
                            Decimal('1000.01'), prize.minimumbid - Decimal('2000.00')
                        ),
                        min_time=prize.end_draw_time() + datetime.timedelta(seconds=1),
                    )
                donation.save()
        eligibleDonors = prize.eligible_donors()
        self.assertEqual({largestDonor}, set(eligibleDonors))
        self.assertEqual(largestAmount, eligibleDonors[largestDonor])
        for seed in [9524, 373, 747]:
            prize.claims.all().delete()
            prize.save()
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertEqual(largestDonor.id, prize.get_winners()[0].id)
        newDonor = randgen.generate_donor(self.rand)
        newDonor.save()
        newDonation = randgen.generate_donation(
            self.rand,
            donor=newDonor,
            event=self.event,
            min_amount=Decimal('1000.01'),
            max_amount=Decimal('2000.00'),
            min_time=prize.start_draw_time(),
            max_time=prize.end_draw_time(),
        )
        newDonation.save()
        eligibleDonors = prize.eligible_donors()
        self.assertEqual({newDonor}, set(eligibleDonors))
        self.assertEqual(newDonation.amount, eligibleDonors[newDonor])
        for seed in [9524, 373, 747]:
            prize.claims.all().delete()
            prize.save()
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertEqual(newDonor.id, prize.get_winners()[0].id)

    def test_draw_prize_multiple_donors_norandom_sum(self):
        startRun = self.runsList[5]
        endRun = self.runsList[9]
        prize = randgen.generate_prize(
            self.rand,
            event=self.event,
            sum_donations=True,
            random_draw=False,
            start_run=startRun,
            end_run=endRun,
        )
        prize.save()
        donationDonors = defaultdict(lambda: Decimal('0.00'))
        for donor in self.donorList:
            numDonations = self.rand.getrandbits(4)
            redHerrings = self.rand.getrandbits(4)
            for i in range(0, numDonations):
                donation = randgen.generate_donation(
                    self.rand,
                    donor=donor,
                    event=self.event,
                    min_amount=Decimal('0.01'),
                    max_amount=Decimal('100.00'),
                    min_time=prize.start_draw_time(),
                    max_time=prize.end_draw_time(),
                )
                donation.save()
                donationDonors[donor] += donation.amount
            # toss in a few extras to keep the drawer on its toes
            for i in range(0, redHerrings):
                if self.rand.getrandbits(1) == 0:
                    donation = randgen.generate_donation(
                        self.rand,
                        donor=donor,
                        event=self.event,
                        min_amount=Decimal('1000.01'),
                        max_amount=Decimal('2000.00'),
                        max_time=prize.start_draw_time()
                        - datetime.timedelta(seconds=1),
                    )
                else:
                    donation = randgen.generate_donation(
                        self.rand,
                        donor=donor,
                        event=self.event,
                        min_amount=Decimal('1000.01'),
                        max_amount=max(
                            Decimal('1000.01'), prize.minimumbid - Decimal('2000.00')
                        ),
                        min_time=prize.end_draw_time() + datetime.timedelta(seconds=1),
                    )
                donation.save()
        maxDonor = max(donationDonors, key=lambda x: donationDonors[x])
        eligibleDonors = prize.eligible_donors()
        self.assertEqual({maxDonor}, set(eligibleDonors))
        self.assertEqual(donationDonors[maxDonor], eligibleDonors[maxDonor])
        for seed in [9524, 373, 747]:
            prize.claims.all().delete()
            prize.save()
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertEqual([maxDonor], prize.get_winners())
        oldMax = donationDonors[maxDonor]
        del donationDonors[maxDonor]
        maxDonor = max(donationDonors, key=lambda x: donationDonors[x])
        diff = oldMax - donationDonors[maxDonor]
        newDonor = maxDonor
        newDonation = randgen.generate_donation(
            self.rand,
            donor=newDonor,
            event=self.event,
            min_amount=diff + Decimal('0.01'),
            max_amount=diff + Decimal('100.00'),
            min_time=prize.start_draw_time(),
            max_time=prize.end_draw_time(),
        )
        newDonation.save()
        donationDonors[maxDonor] += newDonation.amount
        prize = models.Prize.objects.get(id=prize.id)
        eligibleDonors = prize.eligible_donors()
        self.assertEqual({maxDonor}, set(eligibleDonors))
        self.assertEqual(donationDonors[maxDonor], eligibleDonors[maxDonor])
        for seed in [9524, 373, 747]:
            prize.claims.all().delete()
            prize.save()
            result, message = prizeutil.draw_prize(prize, seed)
            self.assertTrue(result)
            self.assertEqual([maxDonor], prize.get_winners())


class TestDonorPrizeEntryDraw(TransactionTestCase):
    def setUp(self):
        self.rand = random.Random(9239234)
        self.event = randgen.generate_event(self.rand)
        self.event.save()

    def testSingleEntry(self):
        donor = randgen.generate_donor(self.rand)
        donor.save()
        prize = randgen.generate_prize(self.rand, event=self.event)
        prize.save()
        entry = models.DonorPrizeEntry(donor=donor, prize=prize)
        entry.save()
        eligible = prize.eligible_donors()
        self.assertEqual(1, len(eligible))
        self.assertIn(donor, eligible)
        self.assertEqual(eligible[donor], prize.minimumbid)

    def testMultipleEntries(self):
        prize = randgen.generate_prize(self.rand, event=self.event)
        prize.save()
        donors = randgen.generate_donors(self.rand, 5)
        models.DonorPrizeEntry.objects.bulk_create(
            models.DonorPrizeEntry(donor=donor, prize=prize) for donor in donors
        )
        self.assertEqual(set(prize.eligible_donors()), set(donors))


class TestPersistentPrizeWinners(TransactionTestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand)
        self.event.save()

    # checks that a prize with a single eligible winner keeps track of a
    # declined prize, and disallows that person from being drawn again

    def test_decline_prize_single(self):
        amount = Decimal('50.0')
        targetPrize = randgen.generate_prize(
            self.rand,
            event=self.event,
            sum_donations=False,
            random_draw=False,
            min_amount=amount,
            maxwinners=1,
        )
        targetPrize.save()
        self.assertEqual(0, len(targetPrize.eligible_donors()))
        donorA = randgen.generate_donor(self.rand)
        donorA.save()
        donorB = randgen.generate_donor(self.rand)
        donorB.save()
        donationA = randgen.generate_donation(
            self.rand,
            donor=donorA,
            min_amount=amount,
            max_amount=amount,
            event=self.event,
        )
        donationA.save()
        self.assertEqual({donorA}, set(targetPrize.eligible_donors()))
        models.PrizeClaim.objects.create(
            prize=targetPrize, winner=donorA, declinecount=1
        ).save()
        self.assertFalse(targetPrize.eligible_donors())
        donationB = randgen.generate_donation(
            self.rand,
            donor=donorB,
            min_amount=amount,
            max_amount=amount,
            event=self.event,
        )
        donationB.save()
        self.assertEqual({donorB}, set(targetPrize.eligible_donors()))

    def test_cannot_exceed_max_winners(self):
        targetPrize = randgen.generate_prize(self.rand, event=self.event)
        targetPrize.maxwinners = 2
        targetPrize.save()
        numDonors = 4
        donors = []
        for i in range(0, numDonors):
            donor = randgen.generate_donor(self.rand)
            donor.save()
            donors.append(donor)
        pw0 = models.PrizeClaim(winner=donors[0], prize=targetPrize)
        pw0.clean()
        pw0.save()
        pw1 = models.PrizeClaim(winner=donors[1], prize=targetPrize)
        pw1.clean()
        pw1.save()
        with self.assertRaises(ValidationError):
            pw2 = models.PrizeClaim(winner=donors[2], prize=targetPrize)
            pw2.clean()
        pw0.pendingcount = 0
        pw0.declinecount = 1
        pw0.save()
        pw2.clean()
        pw2.save()

    def test_redraw_expired_winners(self):
        prize = randgen.generate_prize(self.rand, event=self.event)
        prize.save()
        donors = randgen.generate_donors(self.rand, 2)
        donation = randgen.generate_donation_for_prize(
            self.rand, prize, donor=donors[1]
        )
        donation.save()
        ow = models.PrizeClaim.objects.create(
            prize=prize, winner=donors[0], acceptdeadline=tomorrow_noon
        )
        self.assertFalse(prizeutil.draw_prize(prize)[0])
        ow.acceptdeadline = long_ago_noon
        ow.save()
        drawn, result = prizeutil.draw_prize(prize)
        self.assertTrue(drawn)
        self.assertEqual(result['winners'][0], donors[1].id)
        self.assertSetEqual(
            set(nw.winner for nw in prize.get_prize_claims()), {donors[1]}
        )
        ow.refresh_from_db()
        self.assertEqual(ow.pendingcount, 0)
        self.assertEqual(ow.declinecount, 1)


class TestPrizeCountryFilter(TransactionTestCase):
    fixtures = ['countries']

    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.build_random_event(self.rand)
        self.event.save()

    def testCountryFilterEvent(self):
        countries = list(models.Country.objects.all()[0:4])
        self.event.allowed_prize_countries.add(countries[0])
        self.event.allowed_prize_countries.add(countries[1])
        self.event.save()
        prize = models.Prize.objects.create(event=self.event)
        donors = []
        for country in countries:
            donor = randgen.generate_donor(self.rand)
            donor.addresscountry = country
            donor.save()
            donors.append(donor)
            randgen.generate_donation(
                self.rand,
                event=self.event,
                donor=donor,
                min_amount=Decimal(prize.minimumbid),
            ).save()

        self.assertTrue(prize.is_donor_allowed_to_receive(donors[0]))
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[1]))
        self.assertFalse(prize.is_donor_allowed_to_receive(donors[2]))
        self.assertFalse(prize.is_donor_allowed_to_receive(donors[3]))
        eligible = prize.eligible_donors()
        self.assertEqual(2, len(eligible))
        # Test a different country set
        self.event.allowed_prize_countries.add(countries[3])
        self.event.save()
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[0]))
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[1]))
        self.assertFalse(prize.is_donor_allowed_to_receive(donors[2]))
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[3]))
        eligible = prize.eligible_donors()
        self.assertEqual(3, len(eligible))
        # Test a blank country set
        self.event.allowed_prize_countries.clear()
        self.event.save()
        for donor in donors:
            self.assertTrue(prize.is_donor_allowed_to_receive(donor))
        eligible = prize.eligible_donors()
        self.assertEqual(4, len(eligible))

    def testCountryFilterPrize(self):
        # TODO: fix this so either there's less boilerplate, or the boilerplate is shared
        countries = list(models.Country.objects.all()[0:4])
        prize = models.Prize.objects.create(event=self.event)
        for country in countries[0:3]:
            self.event.allowed_prize_countries.add(country)
        self.event.save()
        prize.allowed_prize_countries.add(countries[0])
        prize.allowed_prize_countries.add(countries[1])
        prize.save()
        donors = []
        for country in countries:
            donor = randgen.generate_donor(self.rand)
            donor.addresscountry = country
            donor.save()
            donors.append(donor)
            randgen.generate_donation(
                self.rand,
                event=self.event,
                donor=donor,
                min_amount=Decimal(prize.minimumbid),
            ).save()
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[0]))
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[1]))
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[2]))
        self.assertFalse(prize.is_donor_allowed_to_receive(donors[3]))
        # by default don't use the prize filter
        eligible = prize.eligible_donors()
        self.assertEqual(3, len(eligible))

        prize.custom_country_filter = True
        prize.save()
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[0]))
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[1]))
        self.assertFalse(prize.is_donor_allowed_to_receive(donors[2]))
        self.assertFalse(prize.is_donor_allowed_to_receive(donors[3]))
        eligible = prize.eligible_donors()
        self.assertEqual(2, len(eligible))
        # Test a different country set
        prize.allowed_prize_countries.add(countries[3])
        prize.save()
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[0]))
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[1]))
        self.assertFalse(prize.is_donor_allowed_to_receive(donors[2]))
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[3]))
        eligible = prize.eligible_donors()
        self.assertEqual(3, len(eligible))
        # Test a blank country set
        prize.allowed_prize_countries.clear()
        prize.save()
        for donor in donors:
            self.assertTrue(prize.is_donor_allowed_to_receive(donor))
        eligible = prize.eligible_donors()
        self.assertEqual(4, len(eligible))

    def testCountryRegionBlacklistFilterEvent(self):
        # Somewhat ethnocentric testing
        country = models.Country.objects.all()[0]
        prize = models.Prize.objects.create(event=self.event)
        donors = []
        allowedState = 'StateOne'
        disallowedState = 'StateTwo'
        for state in [allowedState, disallowedState]:
            donor = randgen.generate_donor(self.rand)
            donor.addresscountry = country
            donor.addressstate = state
            donor.save()
            donors.append(donor)
            randgen.generate_donation(
                self.rand,
                event=self.event,
                donor=donor,
                min_amount=Decimal(prize.minimumbid),
            ).save()

        for donor in donors:
            self.assertTrue(prize.is_donor_allowed_to_receive(donor))
        eligible = prize.eligible_donors()
        self.assertEqual(2, len(eligible))
        # Test a different country set
        countryRegion = models.CountryRegion.objects.create(
            country=country, name=disallowedState
        )
        self.event.disallowed_prize_regions.add(countryRegion)
        self.event.save()
        self.assertTrue(prize.is_donor_allowed_to_receive(donors[0]))
        self.assertFalse(prize.is_donor_allowed_to_receive(donors[1]))
        eligible = prize.eligible_donors()
        self.assertEqual(1, len(eligible))

    def testCountryRegionBlacklistFilterPrize(self):
        # Somewhat ethnocentric testing
        country = models.Country.objects.all()[0]
        prize = models.Prize.objects.create(event=self.event)
        donors = []
        allowedState = 'StateOne'
        disallowedState = 'StateTwo'
        for state in [allowedState, disallowedState]:
            donor = randgen.generate_donor(self.rand)
            donor.addresscountry = country
            donor.addressstate = state
            donor.save()
            donors.append(donor)
            randgen.generate_donation(
                self.rand,
                event=self.event,
                donor=donor,
                min_amount=Decimal(prize.minimumbid),
            ).save()

        eligible = prize.eligible_donors()
        self.assertEqual(2, len(eligible))
        # Test a different country set
        countryRegion = models.CountryRegion.objects.create(
            country=country, name=disallowedState
        )
        prize.disallowed_prize_regions.add(countryRegion)
        prize.custom_country_filter = True
        prize.save()
        eligible = prize.eligible_donors()
        self.assertEqual(1, len(eligible))


class TestPrizeDrawAcceptOffset(TransactionTestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand)
        self.event.save()

    def test_accept_deadline_offset(self):
        # 10 days in the future
        self.event.prize_accept_deadline_delta = 10
        # TODO: it should not take this much set-up to draw a single donor to a single prize
        amount = Decimal('50.0')
        prize = randgen.generate_prize(
            self.rand,
            event=self.event,
            sum_donations=False,
            random_draw=False,
            min_amount=amount,
            maxwinners=1,
        )
        prize.save()
        winner = randgen.generate_donor(self.rand)
        winner.save()
        donation = randgen.generate_donation(
            self.rand,
            donor=winner,
            min_amount=amount,
            max_amount=amount,
            event=self.event,
        )
        donation.save()
        self.assertEqual({winner}, set(prize.eligible_donors()))
        self.assertEqual(0, len(prizeutil.get_past_due_prize_claims(self.event)))
        today = datetime.date.today()
        prizeutil.draw_prize(prize)
        claim = models.PrizeClaim.objects.get(prize=prize)
        self.assertEqual(
            claim.accept_deadline_date(),
            today + datetime.timedelta(days=self.event.prize_accept_deadline_delta),
        )

        claim.acceptdeadline = util.utcnow() - datetime.timedelta(days=2)
        claim.save()
        self.assertEqual(0, len(prize.eligible_donors()))
        pastDue = prizeutil.get_past_due_prize_claims(self.event)
        self.assertEqual(1, len(prizeutil.get_past_due_prize_claims(self.event)))
        self.assertEqual(claim, pastDue[0])


class TestBackfillPrevNextMigrations(MigrationsTestCase):
    migrate_from = [('tracker', '0001_squashed_0020_add_runner_pronouns_and_platform')]
    migrate_to = [('tracker', '0003_populate_prev_next_run')]

    def setUpBeforeMigration(self, apps):
        Prize = apps.get_model('tracker', 'Prize')
        Event = apps.get_model('tracker', 'Event')
        SpeedRun = apps.get_model('tracker', 'SpeedRun')
        self.rand = random.Random(None)
        self.event = Event.objects.create(
            short='test', name='Test Event', datetime=today_noon, targetamount=100
        )
        self.run1 = SpeedRun.objects.create(
            event=self.event, name='Test Run 1', order=1, run_time='0:05:00'
        )
        self.run2 = SpeedRun.objects.create(
            event=self.event, name='Test Run 2', order=2, run_time='0:05:00'
        )
        self.run3 = SpeedRun.objects.create(
            event=self.event, name='Test Run 3', order=3, run_time='0:05:00'
        )
        self.prize1 = Prize.objects.create(
            event=self.event, name='Test Prize 1', startrun=self.run1, endrun=self.run1
        )
        self.prize2 = Prize.objects.create(
            event=self.event, name='Test Prize 2', startrun=self.run2, endrun=self.run2
        )
        self.prize3 = Prize.objects.create(
            event=self.event, name='Test Prize 3', startrun=self.run3, endrun=self.run3
        )

    def test_prev_next_backfilled(self):
        Prize = self.apps.get_model('tracker', 'Prize')
        prize1 = Prize.objects.get(pk=self.prize1.id)
        prize2 = Prize.objects.get(pk=self.prize2.id)
        prize3 = Prize.objects.get(pk=self.prize3.id)
        self.assertEqual(prize1.prev_run_id, None, 'prize 1 prev run incorrect')
        self.assertEqual(prize1.next_run_id, self.run2.id, 'prize 1 next run incorrect')
        self.assertEqual(prize2.prev_run_id, self.run1.id, 'prize 2 prev run incorrect')
        self.assertEqual(prize2.next_run_id, self.run3.id, 'prize 2 next run incorrect')
        self.assertEqual(prize3.prev_run_id, self.run2.id, 'prize 3 prev run incorrect')
        self.assertEqual(prize3.next_run_id, None, 'prize 3 next run incorrect')


class TestPrizeSignals(TestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand)
        self.event.save()
        self.runs = randgen.generate_runs(self.rand, self.event, 4, ordered=True)
        self.event_prize = models.Prize.objects.create(
            name='Event Wide Prize', startrun=self.runs[0], endrun=self.runs[3]
        )
        self.start_prize = models.Prize.objects.create(
            name='Start Prize', startrun=self.runs[0], endrun=self.runs[0]
        )
        self.middle_prize = models.Prize.objects.create(
            name='Middle Prize', startrun=self.runs[1], endrun=self.runs[1]
        )
        self.end_prize = models.Prize.objects.create(
            name='End Prize', startrun=self.runs[3], endrun=self.runs[3]
        )
        self.start_span_prize = models.Prize.objects.create(
            name='Start Span Prize', startrun=self.runs[0], endrun=self.runs[1]
        )
        self.middle_span_prize = models.Prize.objects.create(
            name='Middle Span Prize', startrun=self.runs[1], endrun=self.runs[2]
        )
        self.end_span_prize = models.Prize.objects.create(
            name='End Span Prize', startrun=self.runs[2], endrun=self.runs[3]
        )

    def refresh_all(self):
        for model in [
            self.event,
            self.event_prize,
            self.start_prize,
            self.middle_prize,
            self.end_prize,
            self.start_span_prize,
            self.middle_span_prize,
            self.end_span_prize,
        ] + self.runs:
            try:
                model.refresh_from_db()
            except ObjectDoesNotExist:
                pass  # deleted as part of test

    def test_initial_state(self):
        self.assertEqual(self.event_prize.prev_run, None)
        self.assertEqual(self.event_prize.next_run, None)
        self.assertEqual(self.start_prize.prev_run, None)
        self.assertEqual(self.start_prize.next_run, self.runs[1])
        self.assertEqual(self.middle_prize.prev_run, self.runs[0])
        self.assertEqual(self.middle_prize.next_run, self.runs[2])
        self.assertEqual(self.end_prize.prev_run, self.runs[2])
        self.assertEqual(self.end_prize.next_run, None)
        self.assertEqual(self.start_span_prize.prev_run, None)
        self.assertEqual(self.start_span_prize.next_run, self.runs[2])
        self.assertEqual(self.middle_span_prize.prev_run, self.runs[0])
        self.assertEqual(self.middle_span_prize.next_run, self.runs[3])
        self.assertEqual(self.end_span_prize.prev_run, self.runs[1])
        self.assertEqual(self.end_span_prize.next_run, None)

    def test_run_inserted(self):
        self.runs[3].order = self.runs[2].order = None
        models.SpeedRun.objects.bulk_update((self.runs[2], self.runs[3]), ['order'])
        self.runs[3].order = 5
        self.runs[2].order = 4
        models.SpeedRun.objects.bulk_update((self.runs[2], self.runs[3]), ['order'])
        self.new_run = models.SpeedRun(
            event=self.event, name='New Run', run_time='0:05:00', order=3
        )
        self.new_run.save()
        self.refresh_all()
        self.assertEqual(self.event_prize.prev_run, None)
        self.assertEqual(self.event_prize.next_run, None)
        self.assertEqual(self.start_prize.prev_run, None)
        self.assertEqual(self.start_prize.next_run, self.runs[1])
        self.assertEqual(self.middle_prize.prev_run, self.runs[0])
        self.assertEqual(self.middle_prize.next_run, self.new_run)
        self.assertEqual(self.end_prize.prev_run, self.runs[2])
        self.assertEqual(self.end_prize.next_run, None)
        self.assertEqual(self.start_span_prize.prev_run, None)
        self.assertEqual(self.start_span_prize.next_run, self.new_run)
        self.assertEqual(self.middle_span_prize.prev_run, self.runs[0])
        self.assertEqual(self.middle_span_prize.next_run, self.runs[3])
        self.assertEqual(self.end_span_prize.prev_run, self.new_run)
        self.assertEqual(self.end_span_prize.next_run, None)

    def test_first_run_removed_from_order(self):
        self.runs[0].order = None
        self.runs[0].save()
        self.refresh_all()
        self.assertEqual(self.event_prize.prev_run, None)
        self.assertEqual(self.event_prize.next_run, None)
        self.assertEqual(self.start_prize.prev_run, None)
        self.assertEqual(self.start_prize.next_run, None)
        self.assertEqual(self.middle_prize.prev_run, None)
        self.assertEqual(self.middle_prize.next_run, self.runs[2])
        self.assertEqual(self.end_prize.prev_run, self.runs[2])
        self.assertEqual(self.end_prize.next_run, None)
        self.assertEqual(self.start_span_prize.prev_run, None)
        self.assertEqual(self.start_span_prize.next_run, None)
        self.assertEqual(self.middle_span_prize.prev_run, None)
        self.assertEqual(self.middle_span_prize.next_run, self.runs[3])
        self.assertEqual(self.end_span_prize.prev_run, self.runs[1])
        self.assertEqual(self.end_span_prize.next_run, None)

    def test_first_run_deleted(self):
        self.event_prize.startrun = self.runs[1]
        self.event_prize.save()
        self.start_prize.delete()
        self.start_span_prize.delete()
        self.runs[0].delete()
        self.refresh_all()
        self.assertEqual(self.event_prize.prev_run, None)
        self.assertEqual(self.event_prize.next_run, None)
        self.assertEqual(self.middle_prize.prev_run, None)
        self.assertEqual(self.middle_prize.next_run, self.runs[2])
        self.assertEqual(self.end_prize.prev_run, self.runs[2])
        self.assertEqual(self.end_prize.next_run, None)
        self.assertEqual(self.middle_span_prize.prev_run, None)
        self.assertEqual(self.middle_span_prize.next_run, self.runs[3])
        self.assertEqual(self.end_span_prize.prev_run, self.runs[1])
        self.assertEqual(self.end_span_prize.next_run, None)

    def test_second_run_removed_from_order(self):
        self.runs[1].order = None
        self.runs[1].save()
        self.refresh_all()
        self.assertEqual(self.event_prize.prev_run, None)
        self.assertEqual(self.event_prize.next_run, None)
        self.assertEqual(self.start_prize.prev_run, None)
        self.assertEqual(self.start_prize.next_run, self.runs[2])
        self.assertEqual(self.middle_prize.prev_run, None)
        self.assertEqual(self.middle_prize.next_run, None)
        self.assertEqual(self.end_prize.prev_run, self.runs[2])
        self.assertEqual(self.end_prize.next_run, None)
        self.assertEqual(self.start_span_prize.prev_run, None)
        self.assertEqual(self.start_span_prize.next_run, None)
        self.assertEqual(self.middle_span_prize.prev_run, None)
        self.assertEqual(self.middle_span_prize.next_run, None)
        self.assertEqual(self.end_span_prize.prev_run, self.runs[0])
        self.assertEqual(self.end_span_prize.next_run, None)

    def test_second_run_deleted(self):
        self.start_span_prize.delete()
        self.middle_prize.delete()
        self.middle_span_prize.delete()
        self.runs[1].delete()
        self.refresh_all()
        self.assertEqual(self.event_prize.prev_run, None)
        self.assertEqual(self.event_prize.next_run, None)
        self.assertEqual(self.start_prize.prev_run, None)
        self.assertEqual(self.start_prize.next_run, self.runs[2])
        self.assertEqual(self.end_prize.prev_run, self.runs[2])
        self.assertEqual(self.end_prize.next_run, None)
        self.assertEqual(self.end_span_prize.prev_run, self.runs[0])
        self.assertEqual(self.end_span_prize.next_run, None)

    def test_third_run_removed_from_order(self):
        self.runs[2].order = None
        self.runs[2].save()
        self.refresh_all()
        self.assertEqual(self.event_prize.prev_run, None)
        self.assertEqual(self.event_prize.next_run, None)
        self.assertEqual(self.start_prize.prev_run, None)
        self.assertEqual(self.start_prize.next_run, self.runs[1])
        self.assertEqual(self.middle_prize.prev_run, self.runs[0])
        self.assertEqual(self.middle_prize.next_run, self.runs[3])
        self.assertEqual(self.end_prize.prev_run, self.runs[1])
        self.assertEqual(self.end_prize.next_run, None)
        self.assertEqual(self.start_span_prize.prev_run, None)
        self.assertEqual(self.start_span_prize.next_run, self.runs[3])
        self.assertEqual(self.middle_span_prize.prev_run, None)
        self.assertEqual(self.middle_span_prize.next_run, None)
        self.assertEqual(self.end_span_prize.prev_run, None)
        self.assertEqual(self.end_span_prize.next_run, None)

    def test_third_run_deleted(self):
        self.middle_span_prize.delete()
        self.end_span_prize.delete()
        self.runs[2].delete()
        self.refresh_all()
        self.assertEqual(self.event_prize.prev_run, None)
        self.assertEqual(self.event_prize.next_run, None)
        self.assertEqual(self.start_prize.prev_run, None)
        self.assertEqual(self.start_prize.next_run, self.runs[1])
        self.assertEqual(self.middle_prize.prev_run, self.runs[0])
        self.assertEqual(self.middle_prize.next_run, self.runs[3])
        self.assertEqual(self.end_prize.prev_run, self.runs[1])
        self.assertEqual(self.end_prize.next_run, None)
        self.assertEqual(self.start_span_prize.prev_run, None)
        self.assertEqual(self.start_span_prize.next_run, self.runs[3])

    def test_fourth_run_removed_from_order(self):
        self.runs[3].order = None
        self.runs[3].save()
        self.refresh_all()
        self.assertEqual(self.event_prize.prev_run, None)
        self.assertEqual(self.event_prize.next_run, None)
        self.assertEqual(self.start_prize.prev_run, None)
        self.assertEqual(self.start_prize.next_run, self.runs[1])
        self.assertEqual(self.middle_prize.prev_run, self.runs[0])
        self.assertEqual(self.middle_prize.next_run, self.runs[2])
        self.assertEqual(self.end_prize.prev_run, None)
        self.assertEqual(self.end_prize.next_run, None)
        self.assertEqual(self.start_span_prize.prev_run, None)
        self.assertEqual(self.start_span_prize.next_run, self.runs[2])
        self.assertEqual(self.middle_span_prize.prev_run, self.runs[0])
        self.assertEqual(self.middle_span_prize.next_run, None)
        self.assertEqual(self.end_span_prize.prev_run, None)
        self.assertEqual(self.end_span_prize.next_run, None)

    def test_fourth_run_deleted(self):
        self.end_prize.delete()
        self.end_span_prize.delete()
        self.event_prize.endrun = self.runs[2]
        self.event_prize.save()
        self.runs[3].delete()
        self.refresh_all()
        self.assertEqual(self.event_prize.prev_run, None)
        self.assertEqual(self.event_prize.next_run, None)
        self.assertEqual(self.start_prize.prev_run, None)
        self.assertEqual(self.start_prize.next_run, self.runs[1])
        self.assertEqual(self.middle_prize.prev_run, self.runs[0])
        self.assertEqual(self.middle_prize.next_run, self.runs[2])
        self.assertEqual(self.start_span_prize.prev_run, None)
        self.assertEqual(self.start_span_prize.next_run, self.runs[2])
        self.assertEqual(self.middle_span_prize.prev_run, self.runs[0])
        self.assertEqual(self.middle_span_prize.next_run, None)


class TestPrizeTimeRange(TestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand)
        self.event.save()
        self.runs = randgen.generate_runs(self.rand, self.event, 4, ordered=True)


class TestPrizeKey(TestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand)
        self.event.save()
        self.run = randgen.generate_run(self.rand, self.event)
        self.run.order = 1
        self.run.save()
        self.prize = randgen.generate_prize(
            self.rand,
            event=self.event,
            start_run=self.run,
            end_run=self.run,
            random_draw=True,
        )
        self.prize.key_code = True
        self.prize.save()
        self.prize_keys = randgen.generate_prize_keys(self.rand, self.prize, 100)
        self.prize.refresh_from_db()

    def test_leave_winners_alone_for_non_key_code(self):
        self.prize.key_code = False
        self.prize.requiresshipping = True
        self.prize.maxwinners = 10
        self.prize.save()
        self.assertTrue(self.prize.requiresshipping)
        self.assertEqual(self.prize.maxwinners, 10)

    def test_set_winners_to_key_number_on_prize_save(self):
        self.prize.maxwinners = 1
        self.prize.requiresshipping = True
        self.prize.save()
        self.assertFalse(self.prize.requiresshipping)
        self.assertEqual(self.prize.maxwinners, self.prize.prize_keys.count())

    def test_set_winners_to_key_number_on_prize_key_create(self):
        old_count = self.prize.maxwinners
        randgen.generate_prize_key(self.rand, self.prize).save()
        self.prize.refresh_from_db()
        self.assertEqual(self.prize.maxwinners, old_count + 1)
        self.assertEqual(self.prize.maxwinners, self.prize.prize_keys.count())

    def test_fewer_donors_than_keys(self):
        self.prize.save()
        donor_count = len(self.prize_keys) // 2
        models.Donor.objects.bulk_create(
            [randgen.generate_donor(self.rand) for _ in range(donor_count)]
        )
        # only Postgres returns the objects with pks, so refetch
        donors = list(models.Donor.objects.order_by('-id')[:donor_count])
        models.Donation.objects.bulk_create(
            [
                randgen.generate_donation_for_prize(self.rand, self.prize, donor=d)
                for d in donors
            ]
        )
        self.assertSetEqual(set(self.prize.eligible_donors()), set(donors))
        success, result = prizeutil.draw_keys(self.prize, rand=self.rand)
        self.assertTrue(success, result)
        self.assertSetEqual(set(result['winners']), {d.id for d in donors})
        self.assertSetEqual(
            {k.winner.id for k in self.prize.prize_keys.all() if k.winner},
            {d.id for d in donors},
        )
        self.assertQuerySetEqual(
            self.prize.prize_keys.filter(
                prize_claim__winner__in=donors,
                prize_claim__pendingcount=0,
                prize_claim__acceptcount=1,
                prize_claim__declinecount=0,
                prize_claim__winneremailsent=True,
                prize_claim__acceptemailsentcount=1,
                prize_claim__shippingstate='AWARDED',
                prize_claim__shippingemailsent=False,
            ),
            self.prize.prize_keys.exclude(prize_claim__winner=None),
        )

    def test_draw_with_claimed_keys(self):
        self.prize.save()
        old_donors = set(randgen.generate_donors(self.rand, len(self.prize_keys) // 2))
        old_ids = {d.id for d in old_donors}
        models.Donation.objects.bulk_create(
            [
                randgen.generate_donation_for_prize(self.rand, self.prize, donor=d)
                for d in old_donors
            ]
        )
        self.assertSetEqual(
            set(self.prize.eligible_donors()),
            set(old_donors),
        )
        success, result = prizeutil.draw_keys(self.prize, rand=self.rand)
        self.assertTrue(success, result)

        new_donors = set(randgen.generate_donors(self.rand, len(self.prize_keys) // 2))
        new_ids = {d.id for d in new_donors}
        models.Donation.objects.bulk_create(
            [
                randgen.generate_donation_for_prize(self.rand, self.prize, donor=d)
                for d in new_donors
            ]
        )
        self.assertSetEqual(
            set(self.prize.eligible_donors()),
            set(new_donors),
        )
        success, result = prizeutil.draw_keys(self.prize, rand=self.rand)
        self.assertTrue(success, result)
        self.assertSetEqual(set(result['winners']), new_ids)
        self.assertSetEqual(
            {k.winner.id for k in self.prize.prize_keys.all() if k.winner},
            old_ids | new_ids,
        )
        all_donors = old_donors | new_donors
        self.assertQuerySetEqual(
            self.prize.prize_keys.filter(
                prize_claim__winner__in=all_donors,
                prize_claim__pendingcount=0,
                prize_claim__acceptcount=1,
                prize_claim__declinecount=0,
                prize_claim__winneremailsent=True,
                prize_claim__acceptemailsentcount=1,
                prize_claim__shippingstate='AWARDED',
                prize_claim__shippingemailsent=False,
            ),
            self.prize_keys,
        )

    def test_more_donors_than_keys(self):
        self.prize.save()
        donors = randgen.generate_donors(self.rand, len(self.prize_keys) * 2)
        models.Donation.objects.bulk_create(
            [
                randgen.generate_donation_for_prize(self.rand, self.prize, donor=d)
                for d in donors
            ]
        )
        self.assertSetEqual(set(self.prize.eligible_donors()), set(donors))
        success, result = prizeutil.draw_keys(self.prize, rand=self.rand)
        self.assertTrue(success, result)
        self.assertEqual(self.prize.claims.count(), self.prize.prize_keys.count())
        self.assertQuerySetEqual(
            self.prize.prize_keys.filter(
                prize_claim__winner__in=donors,
                prize_claim__pendingcount=0,
                prize_claim__acceptcount=1,
                prize_claim__declinecount=0,
                prize_claim__winneremailsent=True,
                prize_claim__acceptemailsentcount=1,
                prize_claim__shippingstate='AWARDED',
                prize_claim__shippingemailsent=False,
            ),
            self.prize_keys,
        )

        old_winners = set(result['winners'])
        old_donors = {w.winner.id for w in self.prize.claims.all()}

        self.prize.prize_keys.update(prize_claim=None)
        self.prize.claims.all().delete()

        # assert actual randomness
        success, result = prizeutil.draw_keys(self.prize, rand=self.rand)
        self.assertTrue(success, result)
        self.assertNotEqual(set(result['winners']), old_winners)
        self.assertNotEqual({w.winner.id for w in self.prize.claims.all()}, old_donors)


class TestPrizeAdmin(TestCase, AssertionHelpers):
    def setUp(self):
        self.factory = RequestFactory()
        self.staff_user = User.objects.create_user(
            'staff', 'staff@example.com', 'staff'
        )
        self.staff_user.is_staff = True
        self.staff_user.save()
        self.staff_user.user_permissions.add(
            Permission.objects.get(codename='view_prize')
        )
        self.super_user = User.objects.create_superuser(
            'admin', 'admin@example.com', 'password'
        )
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand)
        self.event.save()
        self.other_event = randgen.generate_event(self.rand, tomorrow_noon)
        self.other_event.save()
        self.prize = randgen.generate_prize(self.rand, event=self.event)
        self.prize.save()
        self.prize_with_keys = randgen.generate_prize(self.rand, event=self.event)
        self.prize_with_keys.key_code = True
        self.prize_with_keys.save()
        self.donor = randgen.generate_donor(self.rand)
        self.donor.save()
        self.no_prizes_donor = randgen.generate_donor(self.rand)
        self.no_prizes_donor.save()
        self.prize_winner = models.PrizeClaim.objects.create(
            winner=self.donor, prize=self.prize
        )
        self.donor_prize_entry = models.DonorPrizeEntry.objects.create(
            donor=self.donor, prize=self.prize
        )
        self.prize_keys = randgen.generate_prize_keys(
            self.rand, self.prize_with_keys, 5
        )
        self.prize_with_keys.refresh_from_db()
        self.prize_contributor_template = create_test_template(
            'Prize Contributor',
            {'event.id', 'handler.id', 'reply_address', 'user_index_url'},
            {'accepted_prizes', 'denied_prizes'},
        )
        self.prize_winner_template = create_test_template(
            'Prize Winner',
            {
                'event',
                'event.id',
                'winner',
                'winner.id',
                'winner.contact_name',
                'requires_shipping',
                'reply_address',
                'accept_deadline',
            },
            extra='{% for claim in claims %}claim_id: {{ claim.id }}\nclaim_url: {{ claim.claim_url}}\n{% endfor %}',
        )
        self.prize_winner_accept_template = create_test_template(
            'Prize Accepted',
            {'user_index_url', 'event.id', 'handler.id', 'reply_address'},
            {'claims'},
        )
        self.prize_shipped_template = create_test_template(
            'Prize Shipped',
            {'event.id', 'winner.contact_name', 'reply_address'},
            extra="""{% for claim in claims %}
claim_id: {{ claim.id }}
claim_url: {{ claim.claim_url}}
{% if claim.prize.key_code %}
claim_key: {{ claim.prize_key.key }}
{% endif %}
{% endfor %}
""",
        )

        self.site = Site.objects.create(name='Public', domain='http://example.com/')

    def test_maximumbid(self):
        with self.assertRaises(ValidationError):
            self.prize.maximumbid = self.prize.minimumbid + 5
            self.prize.clean()

    def test_prize_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_prize_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_prize_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_prize_change', args=(self.prize.id,))
        )
        self.assertEqual(response.status_code, 200)
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('admin:tracker_prize_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Lifecycle')
        response = self.client.get(
            reverse('admin:tracker_prize_change', args=(self.prize.id,))
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Lifecycle')

    def test_prize_key_import_action(self):
        self.client.login(username='admin', password='password')

        response = self.client.post(
            reverse('admin:tracker_prize_changelist'),
            {
                'action': 'import_keys_action',
                ACTION_CHECKBOX_NAME: [self.prize.id, self.prize_with_keys.id],
            },
        )
        self.assertRedirects(response, reverse('admin:tracker_prize_changelist'))
        self.assertMessages(response, ['Select exactly one prize that uses keys.'])
        response = self.client.post(
            reverse('admin:tracker_prize_changelist'),
            {'action': 'import_keys_action', ACTION_CHECKBOX_NAME: [self.prize.id]},
        )
        self.assertRedirects(response, reverse('admin:tracker_prize_changelist'))
        self.assertMessages(response, ['Select exactly one prize that uses keys.'])
        response = self.client.post(
            reverse('admin:tracker_prize_changelist'),
            {
                'action': 'import_keys_action',
                ACTION_CHECKBOX_NAME: [self.prize_with_keys.id],
            },
        )
        self.assertRedirects(
            response,
            reverse('admin:tracker_prize_key_import', args=(self.prize_with_keys.id,)),
        )

    def test_prize_key_import_form(self):
        keys = ['dead-beef-dead-beef-123%d' % i for i in range(5)]
        response = self.client.get(
            reverse('admin:tracker_prize_key_import', args=(self.prize_with_keys.id,))
        )
        self.assertEqual(response.status_code, 302)

        self.client.login(username='staff', password='password')
        response = self.client.get(
            reverse('admin:tracker_prize_key_import', args=(self.prize_with_keys.id,))
        )
        self.assertEqual(response.status_code, 302)

        self.client.login(username='admin', password='password')
        response = self.client.get(
            reverse('admin:tracker_prize_key_import', args=(self.prize.id,))
        )
        self.assertRedirects(response, reverse('admin:tracker_prize_changelist'))
        self.assertMessages(response, ['Cannot import prize keys to non key prizes.'])

        response = self.client.get(
            reverse(
                'admin:tracker_prize_key_import', args=(self.prize_with_keys.id + 1,)
            )
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.get(
            reverse('admin:tracker_prize_key_import', args=(self.prize_with_keys.id,))
        )
        self.assertEqual(response.status_code, 200)

        old_count = self.prize_with_keys.maxwinners
        old_keys = {key.key for key in self.prize_with_keys.prize_keys.all()}

        keys_input = (
            '\n' + ' \n '.join(keys) + '\n%s\n\n' % keys[0]
        )  # test whitespace stripping and deduping
        response = self.client.post(
            reverse('admin:tracker_prize_key_import', args=(self.prize_with_keys.id,)),
            {'keys': keys_input},
        )

        self.assertRedirects(response, reverse('admin:tracker_prize_changelist'))
        self.assertMessages(response, ['5 key(s) added to prize.'])
        self.prize_with_keys.refresh_from_db()
        self.assertEqual(self.prize_with_keys.prize_keys.count(), old_count + 5)
        self.assertEqual(self.prize_with_keys.maxwinners, old_count + 5)
        self.assertSetEqual(
            set(keys),
            {key.key for key in self.prize_with_keys.prize_keys.all()} - old_keys,
        )

        response = self.client.post(
            reverse('admin:tracker_prize_key_import', args=(self.prize_with_keys.id,)),
            {'keys': keys[0]},
        )
        self.assertFormError(
            response.context['form'], 'keys', ['At least one key already exists.']
        )

    def test_prize_winner_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_prizeclaim_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_prizeclaim_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_prizeclaim_change', args=(self.prize_winner.id,))
        )
        self.assertEqual(response.status_code, 200)

    def test_donor_prize_entry_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_donorprizeentry_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_donorprizeentry_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse(
                'admin:tracker_donorprizeentry_change',
                args=(self.donor_prize_entry.id,),
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_prize_key_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin:tracker_prizekey_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_prizekey_change', args=(self.prize_keys[0].id,))
        )
        self.assertEqual(response.status_code, 200)

    def test_prize_mail_contributors(self):
        prize_contributors = []
        for i in range(0, 10):
            prize_contributors.append(
                User.objects.create(
                    username='u' + str(i),
                    email='u' + str(i) + '@email.com',
                    is_active=True,
                )
            )
        prizes = []
        for _ in range(20):
            prizes.append(
                randgen.generate_prize(
                    self.rand,
                    event=self.other_event,
                    handler=self.rand.choice(prize_contributors),
                )
            )
            prizes[-1].save()
        accept_count = 0
        deny_count = 0
        pending_count = 0
        contributor_prizes = defaultdict(lambda: {'accepted': [], 'denied': []})
        for prize in prizes:
            prize.handler = self.rand.choice(prize_contributors)
            state = self.rand.choice(['ACCEPTED', 'DENIED', 'PENDING'])
            prize.state = state
            if state == 'ACCEPTED':
                accept_count += 1
                contributor_prizes[prize.handler]['accepted'].append(prize)
            elif state == 'DENIED':
                deny_count += 1
                contributor_prizes[prize.handler]['denied'].append(prize)
            else:
                pending_count += 1
            prize.save()

        pending_prizes = reduce(
            lambda x, y: x + y['accepted'] + y['denied'],
            contributor_prizes.values(),
            [],
        )
        self.assertSetEqual(
            set(
                models.Prize.objects.filter(
                    event=self.other_event
                ).contributor_email_pending()
            ),
            set(pending_prizes),
        )

        email_count = post_office.models.Email.objects.count()

        self.client.force_login(self.super_user)
        resp = self.client.post(
            reverse(
                'admin:tracker_automail_prize_contributors', args=(self.other_event.id,)
            ),
            data={
                'prizes': [p.id for p in pending_prizes],
                'from_address': 'root@localhost',
                'email_template': self.prize_contributor_template.id,
            },
        )

        self.assertRedirects(resp, reverse('admin:index'))
        self.assertMessages(
            resp,
            [
                f'Mailed prize handler {handler} for {len(handler_prizes["accepted"]) + len(handler_prizes["denied"])} prize(s)'
                for handler, handler_prizes in contributor_prizes.items()
            ],
        )

        self.assertQuerySetEqual(
            models.Prize.objects.filter(event=self.other_event, state='PENDING'),
            models.Prize.objects.filter(event=self.other_event, acceptemailsent=False),
            msg='Pending emails were sent',
        )
        self.assertQuerySetEqual(
            models.Prize.objects.filter(event=self.other_event).exclude(
                state='PENDING'
            ),
            models.Prize.objects.filter(event=self.other_event, acceptemailsent=True),
            msg='Non-pending emails were not sent',
        )
        self.assertEqual(
            email_count + len(contributor_prizes),
            post_office.models.Email.objects.count(),
            msg='Incorrect number of emails',
        )

        for contributor in prize_contributors:
            accepted_prizes = contributor_prizes[contributor]['accepted']
            denied_prizes = contributor_prizes[contributor]['denied']
            contributor_mail = post_office.models.Email.objects.filter(
                to=contributor.email
            ).first()
            if accepted_prizes or denied_prizes:
                parsed = parse_test_mail(contributor_mail)
                self.assertEqual([str(self.other_event.id)], parsed['event.id'])
                self.assertEqual([str(contributor.id)], parsed['handler.id'])
                self.assertEqual(
                    {p.name for p in accepted_prizes},
                    set(parsed.get('accepted_prizes', [])),
                )
                self.assertEqual(
                    {p.name for p in denied_prizes},
                    set(parsed.get('denied_prizes', [])),
                )
            else:
                self.assertIsNone(contributor_mail)

    def test_prize_mail_winners(self):
        self.client.force_login(self.super_user)

        donor2 = randgen.generate_donor(self.rand)
        donor2.save()
        donor3 = randgen.generate_donor(self.rand)
        donor3.save()
        # make a couple key claims to ensure that it doesn't show up in this list, as that's handled by shipped/awarded
        self.prize_keys[0].create_winner(donor2)
        self.prize_keys[1].create_winner(donor3)
        extra_prize = randgen.generate_prize(self.rand, event=self.event)
        extra_prize.save()
        extra_claim = models.PrizeClaim.objects.create(winner=donor2, prize=extra_prize)
        another_extra_prize = randgen.generate_prize(self.rand, event=self.event)
        another_extra_prize.save()
        another_extra_claim = models.PrizeClaim.objects.create(
            winner=donor2, prize=another_extra_prize
        )

        donors = [self.donor, self.no_prizes_donor, donor2, donor3]
        winners = [self.prize_winner, extra_claim, another_extra_claim]

        deadline = (today_noon + datetime.timedelta(days=1)).astimezone(
            anywhere_on_earth_tz()
        )

        self.assertSetEqual(
            {
                c.winner_id
                for c in models.PrizeClaim.objects.filter(
                    prize__event=self.event
                ).winner_email_pending()
            },
            {pw.winner_id for pw in winners},
        )
        resp = self.client.post(
            reverse('admin:tracker_automail_prize_winners', args=(self.event.short,)),
            data={
                'claims': [pw.id for pw in winners],
                'from_address': 'root@localhost',
                'email_template': self.prize_winner_template.id,
                'accept_deadline': deadline.date(),
            },
        )

        self.assertRedirects(resp, reverse('admin:index'))
        self.assertMessages(
            resp,
            {
                f'Mailed Donor {self.donor.email} for 1 won prize claim(s)',
                f'Mailed Donor {donor2.email} for 2 won prize claim(s)',
            },
        )

        for winner in winners:
            winner.refresh_from_db()
            self.assertTrue(
                winner.winneremailsent,
                f'Prize Winner {winner.id} did not have email sent flag set',
            )
            self.assertEqual(
                winner.accept_deadline_date(),
                deadline.date(),
            )

        self.assertEqual(
            post_office.models.Email.objects.count(),
            2,
            'Should have sent 2 total emails',
        )
        for donor in donors:
            won_prizes = models.PrizeClaim.objects.filter(
                winner=donor, prize__key_code=False
            )
            for p in won_prizes:
                with override_settings(TRACKER_PUBLIC_SITE_ID=self.site.id):
                    p.create_claim_url(
                        self.factory.get('/what/ever')
                    )  # test with the site id
            donor_mail = post_office.models.Email.objects.filter(to=donor.email)
            if len(won_prizes) == 0:
                self.assertEqual(
                    0,
                    donor_mail.count(),
                    f'Should not have sent an email to {donor.email}',
                )
            else:
                self.assertEqual(
                    1,
                    donor_mail.count(),
                    f'Should have sent exactly one email to {donor.email}',
                )
                contents = parse_test_mail(donor_mail.first())
                self.assertEqual([str(self.event)], contents['event'])
                self.assertEqual([str(donor)], contents['winner'])
                self.assertEqual([donor.id], [int(w) for w in contents['winner.id']])
                self.assertEqual(
                    [localize(deadline.date())], contents['accept_deadline']
                )
                self.assertSetEqual(
                    {str(p.id) for p in won_prizes},
                    set(contents['claim_id']),
                )
                self.assertSetEqual(
                    {p.claim_url for p in won_prizes}, set(contents['claim_url'])
                )

    def test_preview_prize_winner_mail(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(
            reverse(
                'admin:tracker_preview_prize_winner_mail',
                args=(self.prize_winner.id, self.prize_winner_template.id),
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(post_office.models.Email.objects.count(), 0)

    def test_prize_mail_winner_acceptance(self):
        prize_contributors = []

        for i in range(0, 10):
            prize_contributors.append(
                User.objects.create(
                    username='u' + str(i),
                    email='u' + str(i) + '@email.com',
                    is_active=True,
                )
            )

        prizes = []
        for _ in range(20):
            prizes.append(
                randgen.generate_prize(
                    self.rand,
                    event=self.other_event,
                    handler=self.rand.choice(prize_contributors),
                )
            )
            prizes[-1].save()

        donors = randgen.generate_donors(self.rand, 20)

        prize_claims = defaultdict(list)

        for prize in prizes:
            models.PrizeClaim.objects.create(
                winner=self.rand.choice(donors),
                prize=prize,
                acceptcount=1,
                winneremailsent=True,
                acceptemailsentcount=0,
            )
            prize_claims[prize.handler].append(prize)

        pending_prizes = reduce(lambda x, y: x + y, prize_claims.values(), [])
        self.assertSetEqual(
            set(
                models.PrizeClaim.objects.filter(
                    prize__event=self.other_event
                ).accept_email_pending()
            ),
            set(
                sum((list(p.claims.accept_email_pending()) for p in pending_prizes), [])
            ),
        )

        self.client.force_login(self.super_user)

        resp = self.client.post(
            reverse(
                'admin:tracker_automail_prize_accept_notifications',
                args=(self.other_event.id,),
            ),
            data={
                'claims': [pw.id for p in prizes for pw in p.get_accepted_claims()],
                'from_address': 'root@localhost',
                'email_template': self.prize_winner_accept_template.id,
            },
        )

        self.assertRedirects(resp, reverse('admin:index'))
        self.assertMessages(
            resp,
            {
                f'Mailed handler {handler} for {len(claims)} accepted prize claim(s)'
                for handler, claims in prize_claims.items()
            },
        )

        for contributor in prize_contributors:
            prizes = prize_claims[contributor]
            contributor_mail = post_office.models.Email.objects.filter(
                to=contributor.email
            ).first()
            if prizes:
                parsed = parse_test_mail(contributor_mail)
                self.assertEqual([str(self.other_event.id)], parsed['event.id'])
                self.assertEqual([str(contributor.id)], parsed['handler.id'])
                self.assertEqual(
                    {str(c) for p in prizes for c in p.claims.all()},
                    set(parsed['claims']),
                )
            else:
                self.assertIsNone(contributor_mail)

    def test_prize_mail_shipped(self):
        prizes = []
        for _ in range(20):
            prize = randgen.generate_prize(
                self.rand,
                event=self.other_event,
            )
            prize.save()
            if self.rand.getrandbits(2) == 0:
                prize.key_code = True
                prize.save()
                randgen.generate_prize_keys(self.rand, prize, 5)
            prizes.append(prize)

        donors = randgen.generate_donors(self.rand, 20)

        prize_claims = defaultdict(list)

        for prize in prizes:
            if prize.key_code:
                key_donors = list(donors)
                for key in prize.prize_keys.all():
                    key.prize_claim = models.PrizeClaim.objects.create(
                        winner=self.rand.choice(key_donors),
                        prize=prize,
                        acceptcount=1,
                        winneremailsent=True,
                        acceptemailsentcount=1,
                        shippingstate='AWARDED',
                    )
                    key.save()
                    key_donors.remove(key.prize_claim.winner)
                    prize_claims[key.prize_claim.winner].append(key.prize_claim)
            else:
                claim = models.PrizeClaim.objects.create(
                    winner=self.rand.choice(donors),
                    prize=prize,
                    acceptcount=1,
                    winneremailsent=True,
                    acceptemailsentcount=1,
                    shippingstate='SHIPPED',
                )
                prize_claims[claim.winner].append(claim)

        pending_claims = reduce(operator.add, prize_claims.values(), [])
        self.assertSetEqual(
            set(
                models.PrizeClaim.objects.filter(
                    prize__event=self.other_event
                ).shipped_email_pending()
            ),
            set(pending_claims),
        )

        self.client.force_login(self.super_user)

        resp = self.client.post(
            reverse(
                'admin:tracker_automail_prize_shipping_notifications',
                args=(self.other_event.id,),
            ),
            data={
                'claims': [c.id for c in pending_claims],
                'from_address': 'root@localhost',
                'email_template': self.prize_shipped_template.id,
            },
        )

        self.assertRedirects(resp, reverse('admin:index'))
        self.assertMessages(
            resp,
            {
                f'Mailed donor {winner.email} for {len(claims)} shipped prize(s)'
                for winner, claims in prize_claims.items()
            },
        )

        for winner, claims in prize_claims.items():
            winner_mail = post_office.models.Email.objects.filter(
                to=winner.email
            ).first()

            if claims:
                parsed = parse_test_mail(winner_mail)
                for claim in claims:
                    claim.create_claim_url(self.factory.get('/what/ever'))
                self.assertEqual([str(self.other_event.id)], parsed['event.id'])
                self.assertEqual([winner.contact_name()], parsed['winner.contact_name'])
                self.assertEqual(
                    {c.claim_url for c in claims}, set(parsed['claim_url'])
                )
                self.assertEqual(
                    {c.prize_key.key for c in claims if c.prize.key_code},
                    set(parsed.get('claim_key', [])),
                )
            else:
                self.assertIsNone(winner_mail)

    @patch('tracker.tasks.draw_prize')
    @override_settings(TRACKER_HAS_CELERY=True)
    def test_draw_prize_with_celery(self, task):
        self.client.force_login(self.super_user)
        response = self.client.post(
            reverse('admin:tracker_prize_changelist'),
            {
                'action': 'draw_prize_action',
                ACTION_CHECKBOX_NAME: [self.prize_with_keys.id],
            },
        )
        self.assertRedirects(response, reverse('admin:tracker_prize_changelist'))
        self.assertMessages(response, ['1 prize(s) queued for drawing.'])
        task.delay.assert_called_with(self.prize_with_keys.id)
        task.assert_not_called()

    @patch('tracker.tasks.draw_prize')
    @override_settings(TRACKER_HAS_CELERY=False)
    def test_draw_prize_without_celery(self, task):
        task.return_value = (True, {'winners': []})
        self.client.force_login(self.super_user)
        response = self.client.post(
            reverse('admin:tracker_prize_changelist'),
            {
                'action': 'draw_prize_action',
                ACTION_CHECKBOX_NAME: [self.prize_with_keys.id],
            },
        )
        self.assertRedirects(response, reverse('admin:tracker_prize_changelist'))
        self.assertMessages(response, ['1 prize(s) drawn.'])
        task.assert_called_with(self.prize_with_keys)
        task.delay.assert_not_called()


class TestPrizeList(TestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand, start_time=today_noon)
        self.event.save()

    def test_prize_event_list(self):
        resp = self.client.get(
            reverse(
                'tracker:prizeindex',
            )
        )
        self.assertContains(resp, self.event.name)
        self.assertContains(
            resp, reverse('tracker:prizeindex', args=(self.event.short,))
        )

    def test_prize_list(self):
        regular_prize = randgen.generate_prize(
            self.rand, event=self.event, maxwinners=2
        )
        regular_prize.save()
        # FIXME: we don't display winners any more, but maybe we'll show something else in the future
        # donors = randgen.generate_donors(self.rand, 2)
        # for d in donors:
        #     models.PrizeClaim.objects.create(prize=regular_prize, winner=d)
        # key_prize = randgen.generate_prize(self.rand, event=self.event)
        # key_prize.key_code = True
        # key_prize.save()
        # key_winners = randgen.generate_donors(self.rand, 50)
        # prize_keys = randgen.generate_prize_keys(self.rand, key_prize, 50)
        # for w, k in zip(key_winners, prize_keys):
        #     k.prize_claim = models.PrizeClaim.objects.create(prize=key_prize, winner=w)
        #     k.save()

        response = self.client.get(reverse('tracker:prizeindex', args=(self.event.id,)))
        self.assertNotContains(response, 'Invalid Variable')


class TestPrizeClaim(TestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.coordinator = User.objects.create(username='coordinator')
        self.event = randgen.generate_event(self.rand, start_time=today_noon)
        self.event.prizecoordinator = self.coordinator
        self.event.save()
        randgen.generate_runs(self.rand, self.event, 1, ordered=True)
        self.write_in_prize = randgen.generate_prizes(self.rand, self.event, 1)[0]
        self.write_in_donor = randgen.generate_donors(self.rand, 1)[0]
        self.write_in_claim = models.PrizeClaim.objects.create(
            prize=self.write_in_prize, winner=self.write_in_donor, pendingcount=1
        )
        self.digital_prize = randgen.generate_prize(self.rand, event=self.event)
        self.digital_prize.requiresshipping = False
        self.digital_prize.save()
        self.key_prize = randgen.generate_prize(self.rand, event=self.event)
        self.key_prize.key_code = True
        self.key_prize.save()
        self.keys = randgen.generate_prize_keys(self.rand, self.key_prize, 5)
        self.donation_prize = randgen.generate_prizes(self.rand, self.event, 1)[0]
        self.donation_donor = randgen.generate_donors(self.rand, 1)[0]
        models.Donation.objects.create(
            event=self.event,
            donor=self.donation_donor,
            transactionstate='COMPLETED',
            amount=5,
        )
        self.donation_claim = models.PrizeClaim.objects.create(
            prize=self.donation_prize, winner=self.donation_donor, pendingcount=1
        )
        self.super_user = User.objects.create_superuser(
            'admin', 'nobody@example.com', 'password'
        )

    def test_prize_claim_queryset(self):
        def _get_prize(state):
            prize = randgen.generate_prize(self.rand, event=self.event)
            prize.name = state
            prize.save()
            randgen.assign_prize_lifecycle(self.rand, prize, state)
            return prize

        lifecycle_prizes = {
            state: _get_prize(state)
            for state in [
                'pending',
                'notify_contributor',
                'denied',
                'accepted',
                'drawn',
                'winner_notified',
                'claimed',
                'needs_shipping',
                'shipped',
                'completed',
            ]
        }

        lifecycle_claims = {
            state: prize.claims.all() for state, prize in lifecycle_prizes.items()
        }

        models.PrizeClaim.objects.filter(acceptdeadline=None).update(
            acceptdeadline=today_noon + datetime.timedelta(days=14)
        )

        self.assertEqual(
            {
                self.write_in_claim,
                self.donation_claim,
                *lifecycle_claims['drawn'],
                *lifecycle_claims['winner_notified'],
            },
            set(models.PrizeClaim.objects.pending()),
        )

        deadline = max(
            p.acceptdeadline
            for p in models.PrizeClaim.objects.filter(
                id__in=(
                    p.id
                    for p in (
                        self.write_in_claim,
                        self.donation_claim,
                        *lifecycle_claims['drawn'],
                        *lifecycle_claims['winner_notified'],
                    )
                )
            )
        ) + datetime.timedelta(days=1)

        self.assertEqual(
            set(),
            set(models.PrizeClaim.objects.pending(deadline)),
        )

        self.assertEqual(
            {
                self.write_in_claim,
                self.donation_claim,
                *lifecycle_claims['drawn'],
                *lifecycle_claims['winner_notified'],
            },
            set(models.PrizeClaim.objects.expired(deadline)),
        )

        winner_email_pending = models.PrizeClaim.objects.winner_email_pending()

        self.assertEqual(
            set(winner_email_pending),
            {
                *lifecycle_prizes['drawn'].claims.all(),
                *self.write_in_prize.claims.all(),
                *self.donation_prize.claims.all(),
            },
        )
        self.assertTrue(
            all(
                not pc.winner_email_pending
                for pc in models.PrizeClaim.objects.exclude(
                    id__in=(pc.id for pc in winner_email_pending)
                )
            )
        )
        self.assertTrue(all(pc.winner_email_pending for pc in winner_email_pending))

        self.assertEqual(
            {
                self.donation_claim,
                self.write_in_claim,
                *lifecycle_claims['drawn'],
                *lifecycle_claims['winner_notified'],
                *lifecycle_claims['claimed'],
                *lifecycle_claims['needs_shipping'],
                *lifecycle_claims['shipped'],
                *lifecycle_claims['completed'],
            },
            set(models.PrizeClaim.objects.claimed_or_pending()),
        )

        models.PrizeClaim.objects.decline_expired(deadline)

        self.assertQuerySetEqual(
            models.PrizeClaim.objects.none(), models.PrizeClaim.objects.pending()
        )

        self.assertEqual(
            {
                *lifecycle_claims['claimed'],
                *lifecycle_claims['needs_shipping'],
                *lifecycle_claims['shipped'],
                *lifecycle_claims['completed'],
            },
            set(models.PrizeClaim.objects.claimed_or_pending()),
        )

        accept_email_pending = models.PrizeClaim.objects.accept_email_pending()
        self.assertEqual(
            set(accept_email_pending),
            set(lifecycle_prizes['claimed'].claims.all()),
        )
        self.assertTrue(
            all(
                not pc.accept_email_pending
                for pc in models.PrizeClaim.objects.exclude(
                    id__in=(pc.id for pc in accept_email_pending)
                )
            )
        )
        self.assertTrue(all(pc.accept_email_pending for pc in accept_email_pending))

        self.assertEqual(
            set(lifecycle_claims['needs_shipping']),
            set(models.PrizeClaim.objects.needs_shipping()),
        )

        shipped_email_pending = models.PrizeClaim.objects.shipped_email_pending()
        self.assertEqual(
            set(shipped_email_pending),
            set(lifecycle_claims['shipped']),
        )
        self.assertTrue(
            all(
                not pc.shipped_email_pending
                for pc in models.PrizeClaim.objects.exclude(
                    id__in=(pc.id for pc in shipped_email_pending)
                )
            )
        )
        self.assertTrue(all(pc.shipped_email_pending for pc in shipped_email_pending))

        accepted = lifecycle_prizes['claimed']
        self.event.prizecoordinator = self.super_user
        self.event.save()
        self.assertIn(
            accepted.claims.first(), models.PrizeClaim.objects.accept_email_pending()
        )
        accepted.refresh_from_db()  # ensure that nested event is up to date
        accepted.handler = self.super_user
        accepted.save()
        self.assertNotIn(
            accepted.claims.first(), models.PrizeClaim.objects.accept_email_pending()
        )

        self.assertEqual(
            set(lifecycle_claims['completed']),
            set(models.PrizeClaim.objects.completed()),
        )

    def test_prize_claim_email_fields(self):
        # go through the steps one by one
        self.assertTrue(self.donation_claim.winner_email_pending)
        self.assertFalse(self.donation_claim.accept_email_pending)
        self.assertFalse(self.donation_claim.shipped_email_pending)
        self.donation_claim.winneremailsent = True
        self.assertFalse(self.donation_claim.winner_email_pending)
        self.donation_claim.acceptcount = 1
        self.donation_claim.pendingcount = 0
        self.assertTrue(self.donation_claim.accept_email_pending)
        self.donation_claim.acceptemailsentcount = 1
        self.assertFalse(self.donation_claim.accept_email_pending)
        self.donation_claim.prize.handler = self.coordinator
        self.donation_claim.acceptemailsentcount = 0
        self.donation_claim.save()
        # if the handler is the coordinator, overrides the accepted email count
        self.assertEqual(self.donation_claim.acceptemailsentcount, 1)
        self.assertFalse(self.donation_claim.accept_email_pending)
        self.donation_claim.shippingstate = 'SHIPPED'
        self.assertTrue(self.donation_claim.shipped_email_pending)
        self.donation_claim.shippingemailsent = True
        self.assertFalse(self.donation_claim.shipped_email_pending)

        key_claim = self.keys[0].create_winner(self.donation_donor)
        self.assertEqual(key_claim.acceptcount, 1)
        self.assertEqual(key_claim.pendingcount, 0)
        self.assertEqual(key_claim.declinecount, 0)
        self.assertTrue(key_claim.winneremailsent)
        self.assertEqual(key_claim.acceptemailsentcount, 1)
        self.assertEqual(key_claim.shippingstate, 'AWARDED')
        self.assertFalse(key_claim.winner_email_pending)
        self.assertFalse(key_claim.accept_email_pending)
        self.assertTrue(key_claim.shipped_email_pending)

    def test_prize_winner(self):
        resp = self.client.get(
            f'{reverse("tracker:prize_winner", args=[self.donation_claim.pk])}'
        )
        self.assertEqual(resp.status_code, 404, msg='Missing auth code did not 404')
        resp = self.client.get(
            f'{reverse("tracker:prize_winner", args=[self.donation_claim.pk])}?auth_code={self.write_in_claim.auth_code}'
        )
        self.assertEqual(resp.status_code, 404, msg='Wrong auth code did not 404')
        resp = self.client.get(
            f'{reverse("tracker:prize_winner", args=[self.donation_claim.pk])}?auth_code={self.donation_claim.auth_code}'
        )
        self.assertContains(resp, str(self.donation_prize))

    def test_prize_accept(self):
        resp = self.client.post(
            f'{reverse("tracker:prize_winner", args=[self.donation_claim.pk])}?auth_code={self.donation_claim.auth_code}',
            data={
                'prizeaccept-count': 1,
                'prizeaccept-total': 1,
                'address-addressname': 'Foo Bar',
                'address-addressstreet': '123 Somewhere Lane',
                'address-addresscity': 'Atlantis',
                'address-addressstate': 'NJ',
                'address-addresscountry': models.Country.objects.get(alpha2='US').pk,
                'address-addresszip': 20000,
                'accept': 'Accept',
            },
        )
        self.assertContains(resp, 'You have accepted')
        self.donation_donor.refresh_from_db()
        self.donation_claim.refresh_from_db()
        self.assertEqual(self.donation_donor.addressname, 'Foo Bar')
        self.assertEqual(self.donation_donor.addressstreet, '123 Somewhere Lane')
        self.assertEqual(self.donation_donor.addresscity, 'Atlantis')
        self.assertEqual(self.donation_donor.addressstate, 'NJ')
        self.assertEqual(self.donation_donor.addresscountry.alpha2, 'US')
        self.assertEqual(self.donation_donor.addresszip, '20000')
        self.assertEqual(self.donation_claim.pendingcount, 0, 'Pending count is not 0')
        self.assertEqual(self.donation_claim.acceptcount, 1, 'Accept count is not 1')
        self.assertEqual(self.donation_claim.declinecount, 0, 'Declined count is not 0')
        self.client.force_login(self.super_user)
        resp = self.client.get(
            reverse('tracker:user_prize', args=(self.donation_prize.pk,))
        )
        self.assertContains(resp, self.donation_donor.addressname)

    def test_prize_decline(self):
        resp = self.client.post(
            f'{reverse("tracker:prize_winner", args=[self.write_in_claim.pk])}?auth_code={self.write_in_claim.auth_code}',
            data={
                'prizeaccept-count': 1,
                'prizeaccept-total': 1,
                'address-addressname': 'Foo Bar',
                'address-addressstreet': '123 Somewhere Lane',
                'address-addresscity': 'Atlantis',
                'address-addressstate': 'NJ',
                'address-addresscountry': models.Country.objects.get(alpha2='US').pk,
                'address-addresszip': 20000,
                'decline': 'Decline',
            },
        )
        self.assertContains(resp, 'You have declined')
        self.write_in_donor.refresh_from_db()
        self.write_in_claim.refresh_from_db()
        # a bit weird perhaps, but it still updates the address because it's easier than not doing it
        self.assertEqual(self.write_in_donor.addressname, 'Foo Bar')
        self.assertEqual(self.write_in_donor.addressstreet, '123 Somewhere Lane')
        self.assertEqual(self.write_in_donor.addresscity, 'Atlantis')
        self.assertEqual(self.write_in_donor.addressstate, 'NJ')
        self.assertEqual(self.write_in_donor.addresscountry.alpha2, 'US')
        self.assertEqual(self.write_in_donor.addresszip, '20000')
        self.assertEqual(self.write_in_claim.pendingcount, 0, 'Pending count is not 0')
        self.assertEqual(self.write_in_claim.acceptcount, 0, 'Accept count is not 0')
        self.assertEqual(self.write_in_claim.declinecount, 1, 'Declined count is not 1')
        self.client.force_login(self.super_user)
        resp = self.client.get(
            reverse('tracker:user_prize', args=(self.write_in_prize.pk,))
        )
        self.assertContains(resp, 'There are currently no winners for this prize.')

    def test_prize_already_accepted(self):
        self.donation_claim.acceptcount = 1
        self.donation_claim.pendingcount = 0
        self.donation_claim.save()
        # smoke test to make sure that it doesn't blow up if they refresh the page
        resp = self.client.post(
            f'{reverse("tracker:prize_winner", args=[self.donation_claim.pk])}?auth_code={self.donation_claim.auth_code}',
            data={
                'prizeaccept-count': 1,
                'prizeaccept-total': 1,
                'address-addressname': 'Foo Bar',
                'address-addressstreet': '123 Somewhere Lane',
                'address-addresscity': 'Atlantis',
                'address-addressstate': 'NJ',
                'address-addresscountry': models.Country.objects.get(alpha2='US').pk,
                'address-addresszip': 20000,
                'accept': 'Accept',
            },
        )
        self.assertContains(resp, 'You have accepted')


class TestPrizeClaimUrl(TestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand, start_time=today_noon)
        self.event.save()
        self.prize = randgen.generate_prize(self.rand, event=self.event)
        self.prize.save()
        self.donor = randgen.generate_donor(self.rand)
        self.donor.save()
        self.prize_winner = models.PrizeClaim.objects.create(
            prize=self.prize, winner=self.donor
        )
        self.prize_winner.save()

    @override_settings(
        INSTALLED_APPS=set(settings.INSTALLED_APPS) & {'django.contrib.sites'}
    )
    def test_with_sites_enabled(self):
        from django.contrib.sites.models import Site

        request = RequestFactory().get('/foo/bar')

        site = Site.objects.create(domain='a.site', name='The Site')

        with override_settings(TRACKER_PUBLIC_SITE_ID=site.id):
            self.prize_winner.create_claim_url(request)
            self.assertIn('a.site', self.prize_winner.claim_url)
            self.assertNotIn(request.get_host(), self.prize_winner.claim_url)

    @override_settings(
        INSTALLED_APPS=set(settings.INSTALLED_APPS) ^ {'django.contrib.sites'}
    )
    def test_with_sites_disabled(self):
        request = RequestFactory().get('/foo/bar')

        self.prize_winner.create_claim_url(request)
        self.assertIn(request.get_host(), self.prize_winner.claim_url)


@override_settings(TRACKER_SWEEPSTAKES_URL='')
class TestPrizeNoSweepstakes(TestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.event = randgen.generate_event(self.rand, start_time=today_noon)
        self.event.save()

    def test_prize_index_generic_404(self):
        response = self.client.get(reverse('tracker:prizeindex', args=(self.event.id,)))
        self.assertContains(response, 'Bad page', status_code=404)

    def test_prize_detail_generic_404(self):
        response = self.client.get(reverse('tracker:prize', args=(1,)))
        self.assertContains(response, 'Bad page', status_code=404)

    def test_donate_raises(self):
        with override_settings(
            TRACKER_SWEEPSTAKES_URL='temp'
        ):  # create a worst case scenario
            prize = randgen.generate_prize(self.rand, event=self.event)
            randgen.assign_prize_lifecycle(self.rand, prize, 'accepted')
        with self.assertRaisesRegex(ImproperlyConfigured, 'TRACKER_SWEEPSTAKES_URL'):
            self.client.get(reverse('tracker:ui:donate', args=(self.event.id,)))

    def test_model_invalid(self):
        with self.assertRaisesRegex(ValidationError, 'TRACKER_SWEEPSTAKES_URL'):
            models.Prize(event=self.event).clean()

    def test_model_save_raises(self):
        with self.assertRaisesRegex(ImproperlyConfigured, 'TRACKER_SWEEPSTAKES_URL'):
            models.Prize.objects.create(event=self.event)


class TestPrizeClaimRename(MigrationsTestCase):
    migrate_from = [('tracker', '0070_backfill_donor_cache_enhancements')]
    migrate_to = [('tracker', '0072_rename_prize_claim_permissions')]

    def setUpBeforeMigration(self, apps):
        Permission = apps.get_model('auth', 'Permission')
        User = apps.get_model('auth', 'User')
        Group = apps.get_model('auth', 'Group')
        User.objects.create(username='test_user').user_permissions.add(
            Permission.objects.get(codename='add_prizewinner')
        )
        Group.objects.create(name='Test Group').permissions.add(
            Permission.objects.get(codename='view_prizewinner')
        )

    def test_migrated_permissions(self):
        Permission = self.apps.get_model('auth', 'Permission')
        User = self.apps.get_model('auth', 'User')
        Group = self.apps.get_model('auth', 'Group')
        self.assertTrue(
            User.objects.get(username='test_user')
            .user_permissions.filter(codename='add_prizeclaim')
            .exists()
        )
        self.assertTrue(
            Group.objects.get(name='Test Group')
            .permissions.filter(codename='view_prizeclaim')
            .exists()
        )
        self.assertFalse(
            Permission.objects.filter(codename__endswith='_prizewinner').exists()
        )


class TestPrizeRemoveMaximumBid(MigrationsTestCase):
    migrate_from = [('tracker', '0077_alter_prize_imagefile')]
    migrate_to = [('tracker', '0078_clear_prize_maximumbid')]

    def setUpBeforeMigration(self, apps):
        Prize = apps.get_model('tracker', 'Prize')
        Event = apps.get_model('tracker', 'Event')
        event = Event.objects.create(name='Test Event', datetime=today_noon)
        Prize.objects.create(name='Range', event=event, minimumbid=5, maximumbid=10)
        Prize.objects.create(name='No Range', event=event, minimumbid=5, maximumbid=5)

    def test_after_migration(self):
        Prize = self.apps.get_model('tracker', 'Prize')
        self.assertIsNone(Prize.objects.get(name='No Range').maximumbid)
        self.assertEqual(Prize.objects.get(name='Range').maximumbid, 10)


class TestPrizeSubmission(TestCase, AssertionHelpers):
    def setUp(self):
        super().setUp()
        self.rand = random.Random()
        self.event = randgen.generate_event(self.rand, tomorrow_noon)
        self.event.save()
        self.user = User.objects.create(username='test_user')
        randgen.generate_runs(self.rand, self.event, 5, ordered=True)
        randgen.generate_runs(self.rand, self.event, 1, ordered=False)

    def test_smoke(self):
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse('tracker:submit_prize', args=(self.event.id,)),
            data={
                'event': self.event.id,
                'name': 'Test Prize',
                'description': 'This prize is great.',
                'maxwinners': 1,
                'extrainfo': 'I made this with pink Himalayan sea salt.',
                'estimatedvalue': '5.00',
                'imageurl': 'https://example.com/deadbeef.jpg',
                'creatorname': 'Jesse Doe',
                'creatoremail': 'jesse@example.com',
                'creatorwebsite': 'https://example.com/jesse',
                'agreement': 1,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context['form'].is_valid())
        prize = models.Prize.objects.get(name='Test Prize')
        self.assertDictContainsSubset(
            dict(
                event_id=self.event.id,
                description='This prize is great.',
                maxwinners=1,
                extrainfo='I made this with pink Himalayan sea salt.',
                estimatedvalue=Decimal('5.00'),
                image='https://example.com/deadbeef.jpg',
                creator='Jesse Doe',
                creatoremail='jesse@example.com',
                creatorwebsite='https://example.com/jesse',
            ),
            prize.__dict__,
        )
