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
        self.rand = random.Random(None)
        self.numDonors = 60
        self.numPrizes = 40
        self.event = randgen.build_random_event(
            self.rand, numRuns=20, numPrizes=self.numPrizes, numDonors=self.numDonors)
        self.templateEmail = post_office.models.EmailTemplate.objects.create(
            name="testing_prize_winner_notification", description="", subject="You Win!", content=self.emailTemplate)

    def _parseMail(self, mail):
        contents = test_util.parse_test_mail(mail)
        event = int(contents['event'][0])
        winner = int(contents['winner'][0])
        prizes = list(map(lambda x: int(x), contents.get('prize', [])))
        return event, winner, prizes

    def testAutoMail(self):
        models.Prize.objects.update(state='ACCEPTED')
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
                        models.PrizeWinner.objects.create(winner=winner, prize=prize, pendingcount=1))
                    donorPrizeList = donorWins.get(winner.id, None)
                    if donorPrizeList == None:
                        donorPrizeList = []
                        donorWins[winner.id] = donorPrizeList
                    donorPrizeList.append(prize)

        self.assertItemsEqual(prizemail.prize_winners_with_email_pending(self.event), fullWinnerList)
        prizemail.automail_prize_winners(
            self.event, fullWinnerList, self.templateEmail, sender='nobody@nowhere.com')

        for prizeWinner in fullWinnerList:
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
  PROVIDERID:{{ provider.id }}
  {% for prize in accepted_prizes %}
    ACCEPTED:{{ prize.id }}
  {% endfor %}
  {% for prize in denied_prizes %}
    DENIED:{{ prize.id }}
  {% endfor %}
  """

    def setUp(self):
        self.rand = random.Random(None)
        self.numDonors = 10
        self.numPrizes = 40
        self.event = randgen.build_random_event(
            self.rand, numRuns=20, numPrizes=self.numPrizes, numDonors=self.numDonors)
        self.templateEmail = post_office.models.EmailTemplate.objects.create(
            name="testing_prize_submission_response", description="", subject="A Test", content=self.testTemplateContent)

    def _parseMail(self, mail):
        contents = test_util.parse_test_mail(mail)
        event = int(contents['event'][0])
        providerId = int(contents['providerid'][0])
        accepted = list(map(lambda x: int(x), contents.get('accepted', [])))
        denied = list(map(lambda x: int(x), contents.get('denied', [])))
        return event, providerId, accepted, denied

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

        pendingPrizes = reduce(lambda x,y: x + y[0] + y[1], contributorPrizes.values(), [])
        self.assertItemsEqual(prizemail.prizes_with_submission_email_pending(self.event), pendingPrizes)
        prizemail.automail_prize_contributors(
            self.event, pendingPrizes, self.templateEmail, sender='nobody@nowhere.com')

        for prize in models.Prize.objects.all():
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
                eventId, providerId, acceptedIds, deniedIds = self._parseMail(contributorMail[0])
                self.assertEqual(self.event.id, eventId)
                self.assertEqual(contributor.id, providerId)
                self.assertEqual(len(acceptedPrizes), len(acceptedIds))
                self.assertEqual(len(deniedPrizes), len(deniedIds))
                for prize in acceptedPrizes:
                    self.assertTrue(prize.id in acceptedIds)
                for prize in deniedPrizes:
                    self.assertTrue(prize.id in deniedIds)


class TestAutomailPrizeWinnerAcceptNotifications(TransactionTestCase):
    testTemplateContent = """
        EVENT:{{ event.id }}
        PROVIDERID:{{ provider.id }}
        {% for prizeWin in prize_wins %}
            PRIZEWINNER:{{ prizeWin.id }}
        {% endfor %}
        REPLY:{{ reply_address }}
        """
    
    def setUp(self):
        self.rand = random.Random(None)
        self.numDonors = 20
        self.numPrizes = 30
        self.event = randgen.build_random_event(
            self.rand, numRuns=20, numPrizes=self.numPrizes, numDonors=self.numDonors)
        self.templateEmail = post_office.models.EmailTemplate.objects.create(
            name="testing_prize_accept_notification", description="", subject="A Test", content=self.testTemplateContent)
        self.sender = 'nobody@nowhere.com'

    def _parseMail(self, mail):
        contents = test_util.parse_test_mail(mail)
        event = int(contents['event'][0])
        providerId = int(contents['providerid'][0])
        prizeWins = list(map(lambda x: int(x), contents.get('prizewinner', [])))
        reply = contents['reply'][0]
        return event, providerId, prizeWins, reply

    def testAutomail(self):
        models.Prize.objects.update(state='ACCEPTED')
        prizeContributors = []
        
        for i in range(0,10):
            prizeContributors.append(AuthUser.objects.create(username='u'+str(i),email='u'+str(i)+'@email.com',is_active=True))
            
        prizes = models.Prize.objects.all()
        donors = models.Donor.objects.all()
        contributorPrizeWinners = {}
        
        for contributor in prizeContributors:
            contributorPrizeWinners[contributor] = []
            
        for prize in prizes:
            prize.provider = self.rand.choice(prizeContributors)
            prize.save()
            prizeWinner = models.PrizeWinner.objects.create(
                winner=self.rand.choice(donors),prize=prize,acceptcount=1,pendingcount=0,emailsent=True,acceptemailsentcount=0)
            contributorPrizeWinners[prize.provider].append(prizeWinner)

        winnerList = reduce(lambda x,y: x + y, contributorPrizeWinners.values(), [])
        self.assertItemsEqual(prizemail.prizes_with_winner_accept_email_pending(self.event), winnerList)
        
        prizemail.automail_winner_accepted_prize(
            self.event, winnerList, self.templateEmail, sender=self.sender)
            
        for contributor in prizeContributors:
            prizeWinners = contributorPrizeWinners[contributor]
            contributorMail = post_office.models.Email.objects.filter(to=contributor.email)
            if len(prizeWinners) == 0:
                self.assertEqual(0, contributorMail.count())
            else:
                self.assertEqual(1, contributorMail.count())
                eventId, providerId, mailedPrizeWinnerIds, reply = self._parseMail(contributorMail[0])
                self.assertEqual(self.event.id, eventId)
                self.assertEqual(contributor.id, providerId)
                self.assertEqual(len(mailedPrizeWinnerIds), len(prizeWinners))
                for prizeWinner in prizeWinners:
                    self.assertTrue(prizeWinner.id in mailedPrizeWinnerIds)
                self.assertEqual(self.sender, reply)


class TestAutomailPrizesShipped(TransactionTestCase):
    testTemplateContent = """
        EVENT:{{ event.id }}
        WINNER:{{ winner.id }}
        {% for prizeWin in prize_wins %}
            PRIZEWINNER:{{ prizeWin.id }}
        {% endfor %}
        REPLY:{{ reply_address }}
        """

    def setUp(self):
        self.rand = random.Random(None)
        self.numDonors = 20
        self.numPrizes = 40
        self.event = randgen.build_random_event(
            self.rand, numRuns=20, numPrizes=self.numPrizes, numDonors=self.numDonors)
        self.templateEmail = post_office.models.EmailTemplate.objects.create(
            name="testing_prize_shipping_notification", description="", subject="A Test", content=self.testTemplateContent)
        self.sender = 'nobody@nowhere.com'

    def _parseMail(self, mail):
        contents = test_util.parse_test_mail(mail)
        event = int(contents['event'][0])
        winnerId = int(contents['winner'][0])
        prizeWins = list(map(lambda x: int(x), contents.get('prizewinner', [])))
        reply = contents['reply'][0]
        return event, winnerId, prizeWins, reply

    def testAutomail(self):
        models.Prize.objects.update(state='ACCEPTED')
        prizes = models.Prize.objects.all()
        donors = models.Donor.objects.all()
        winningDonors = {}
        
        for donor in donors:
            winningDonors[donor] = []
            
        for prize in prizes:
            if self.rand.getrandbits(1) == 0:
                prizeWinner = models.PrizeWinner.objects.create(
                    winner=self.rand.choice(donors),prize=prize,acceptcount=1,pendingcount=0,emailsent=True,acceptemailsentcount=1,shippingstate='SHIPPED',shippingemailsent=False)
                winningDonors[prizeWinner.winner].append(prizeWinner)
            
        winnerList = reduce(lambda x,y: x + y, winningDonors.values(), [])
        self.assertItemsEqual(prizemail.prizes_with_shipping_email_pending(self.event), winnerList)
        
        prizemail.automail_shipping_email_notifications(
            self.event, winnerList, self.templateEmail, sender=self.sender)

        for winner in winningDonors:
            prizeWinners = winningDonors[winner]
            winnerMail = post_office.models.Email.objects.filter(to=winner.email)
            
            if len(prizeWinners) == 0:
                self.assertEqual(0, winnerMail.count())
            else:
                self.assertEqual(1, winnerMail.count())
                eventId, winnerId, mailedPrizeWinnerIds, reply = self._parseMail(winnerMail[0])
                self.assertEqual(self.event.id, eventId)
                self.assertEqual(winner.id, winnerId)
                self.assertEqual(len(mailedPrizeWinnerIds), len(prizeWinners))
                for prizeWinner in prizeWinners:
                    self.assertTrue(prizeWinner.id in mailedPrizeWinnerIds)
                self.assertEqual(self.sender, reply)