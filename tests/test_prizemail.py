from decimal import Decimal
import random
import datetime
import pytz

from dateutil.parser import parse as parse_date

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model

import post_office.models

import tracker.models as models
import tracker.randgen as randgen
import tracker.prizemail as prizemail

AuthUser = get_user_model()

import tracker.tests.util as test_util

class TestAutomailPrizeWinners(TransactionTestCase):
    emailTemplate = """
  EVENT:{{ event.id }}
  WINNER:{{ winner.id }}
  {% for prize in prizes %}
    PRIZE: {{ prize.id }}
  {% endfor %}
  """

    def setUp(self):
        self.eventStart = parse_date("2014-02-02 05:00:05")
        self.rand = random.Random(8556142)
        self.numDonors = 60
        self.numPrizes = 400
        self.event = randgen.build_random_event(
            self.rand, startTime=self.eventStart, numRuns=20, numPrizes=self.numPrizes, numDonors=self.numDonors)
        self.templateEmail = post_office.models.EmailTemplate.objects.create(
            name="testing_prize_winner_notification", description="", subject="You Win!", content=self.emailTemplate)

    def _parseMail(self, mail):
        contents = test_util.parse_test_mail(mail)
        event = int(contents['event'][0])
        winner = int(contents['winner'][0])
        prizes = list(map(lambda x: int(x), contents.get('prize', [])))
        return event, winner, prizes

    def testAutoMail(self):
        donors = list(models.Donor.objects.all())
        prizes = list(models.Prize.objects.all())
        fullWinnerList = []
        donorWins = {}
        for prize in prizes:
            if self.rand.getrandbits(1) == 0:
                winners = []
                while len(winners) < prize.maxwinners:
                    d = donors[self.rand.randrange(len(donors))]
                    if d not in winners:
                        winners.append(d)
                for winner in winners:
                    fullWinnerList.append(
                        models.PrizeWinner.objects.create(winner=winner, prize=prize))
                    donorPrizeList = donorWins.get(winner.id, None)
                    if donorPrizeList == None:
                        donorPrizeList = []
                        donorWins[winner.id] = donorPrizeList
                    donorPrizeList.append(prize)
        prizemail.automail_prize_winners(
            self.event, fullWinnerList, self.templateEmail, sender='nobody@nowhere.com')
        prizeWinners = models.PrizeWinner.objects.all()
        self.assertEqual(len(fullWinnerList), prizeWinners.count())
        for prizeWinner in prizeWinners:
            self.assertTrue(prizeWinner.emailsent)
        for donor in donors:
            wonPrizes = donorWins.get(donor.id, [])
            donorMail = post_office.models.Email.objects.filter(to=donor.email)
            if len(wonPrizes) == 0:
                self.assertEqual(0, donorMail.count())
            else:
                self.assertEqual(1, donorMail.count())
                eventId, winnerId, prizeIds = self._parseMail(donorMail[0])
                self.assertEqual(self.event.id, eventId)
                self.assertEqual(donor.id, winnerId)
                self.assertEqual(len(wonPrizes), len(prizeIds))
                for prize in wonPrizes:
                    self.assertTrue(prize.id in prizeIds)


class TestAutomailPrizeContributors(TransactionTestCase):
    testTemplateContent = """
  EVENT:{{ event.id }}
  NAME:{{ contributorName }}
  {% for prize in acceptedPrizes %}
    ACCEPTED:{{ prize.id }}
  {% endfor %}
  {% for prize in deniedPrizes %}
    DENIED:{{ prize.id }}
  {% endfor %}
  """

    def setUp(self):
        self.eventStart = parse_date("2014-02-02 05:00:05")
        self.rand = random.Random(839740)
        self.numDonors = 10
        self.numPrizes = 40
        self.event = randgen.build_random_event(
            self.rand, startTime=self.eventStart, numRuns=20, numPrizes=self.numPrizes, numDonors=self.numDonors)
        self.templateEmail = post_office.models.EmailTemplate.objects.create(
            name="testing_prize_submission_response", description="", subject="A Test", content=self.testTemplateContent)

    def _parseMail(self, mail):
        contents = test_util.parse_test_mail(mail)
        event = int(contents['event'][0])
        name = contents['name'][0]
        accepted = list(map(lambda x: int(x), contents.get('accepted', [])))
        denied = list(map(lambda x: int(x), contents.get('denied', [])))
        return event, name, accepted, denied

    def testAutoMail(self):
        prizeContributors = []
        for i in range(0,10):
            prizeContributors.append(AuthUser.objects.create(username='u'+str(i),email='u'+str(i)+'@email.com',is_active=True))
        prizes = models.Prize.objects.all()
        acceptCount = 0
        denyCount = 0
        pendingCount = 0
        contributorPrizes = {}
        for contributor in prizeContributors:
            contributorPrizes[contributor] = ([], [])
        for prize in prizes:
            prize.provider = self.rand.choice(prizeContributors)
            pickVal = self.rand.randrange(3)
            if pickVal == 0:
                prize.state = "ACCEPTED"
                acceptCount += 1
                contributorPrizes[prize.provider][0].append(prize)
            elif pickVal == 1:
                prize.state = "DENIED"
                denyCount += 1
                contributorPrizes[prize.provider][1].append(prize)
            else:
                prize.state = "PENDING"
                pendingCount += 1
            prize.save()
        processedPrizes = prizemail.prizes_with_submission_email_pending(
            self.event)
        self.assertEqual(acceptCount + denyCount, processedPrizes.count())
        prizemail.automail_prize_contributors(
            self.event, processedPrizes, self.templateEmail, sender='nobody@nowhere.com')
        prizes = models.Prize.objects.all()
        for prize in prizes:
            if prize.state == "PENDING":
                self.assertFalse(prize.acceptemailsent)
            else:
                self.assertTrue(prize.acceptemailsent)
        for contributor in prizeContributors:
            acceptedPrizes, deniedPrizes = contributorPrizes[contributor]
            contributorMail = post_office.models.Email.objects.filter(to=contributor.email)
            if len(acceptedPrizes) == 0 and len(deniedPrizes) == 0:
                self.assertEqual(0, contributorMail.count())
            else:
                self.assertEqual(1, contributorMail.count())
                eventId, name, acceptedIds, deniedIds = self._parseMail(contributorMail[0])
                self.assertEqual(self.event.id, eventId)
                self.assertEqual(contributor.username, name)
                self.assertEqual(len(acceptedPrizes), len(acceptedIds))
                self.assertEqual(len(deniedPrizes), len(deniedIds))
                for prize in acceptedPrizes:
                    self.assertTrue(prize.id in acceptedIds)
                for prize in deniedPrizes:
                    self.assertTrue(prize.id in deniedIds)
