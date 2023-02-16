import random
from functools import reduce

import post_office.models
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase

import tracker.models as models
import tracker.prizemail as prizemail

from . import randgen, util

AuthUser = get_user_model()


class TestAutomailPrizeContributors(TransactionTestCase):
    testTemplateContent = """
  EVENT:{{ event.id }}
  HANDLERID:{{ handler.id }}
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
            self.rand, num_runs=20, num_prizes=self.numPrizes, num_donors=self.numDonors
        )
        self.templateEmail = post_office.models.EmailTemplate.objects.create(
            name='testing_prize_submission_response',
            description='',
            subject='A Test',
            content=self.testTemplateContent,
        )

    def _parseMail(self, mail):
        contents = util.parse_test_mail(mail)
        event = int(contents['event'][0])
        handlerId = int(contents['handlerid'][0])
        accepted = [int(x) for x in contents.get('accepted', [])]
        denied = [int(x) for x in contents.get('denied', [])]
        return event, handlerId, accepted, denied

    def testAutoMail(self):
        prizeContributors = []
        for i in range(0, 10):
            prizeContributors.append(
                AuthUser.objects.create(
                    username='u' + str(i),
                    email='u' + str(i) + '@email.com',
                    is_active=True,
                )
            )
        prizes = models.Prize.objects.all()
        acceptCount = 0
        denyCount = 0
        pendingCount = 0
        contributorPrizes = {}
        for contributor in prizeContributors:
            contributorPrizes[contributor] = ([], [])
        for prize in prizes:
            prize.handler = self.rand.choice(prizeContributors)
            pickVal = self.rand.randrange(3)
            if pickVal == 0:
                prize.state = 'ACCEPTED'
                acceptCount += 1
                contributorPrizes[prize.handler][0].append(prize)
            elif pickVal == 1:
                prize.state = 'DENIED'
                denyCount += 1
                contributorPrizes[prize.handler][1].append(prize)
            else:
                prize.state = 'PENDING'
                pendingCount += 1
            prize.save()

        pendingPrizes = reduce(
            lambda x, y: x + y[0] + y[1], contributorPrizes.values(), []
        )
        self.assertSetEqual(
            set(prizemail.prizes_with_submission_email_pending(self.event)),
            set(pendingPrizes),
        )
        prizemail.automail_prize_contributors(
            self.event, pendingPrizes, self.templateEmail, sender='nobody@nowhere.com'
        )

        for prize in models.Prize.objects.all():
            if prize.state == 'PENDING':
                self.assertFalse(prize.acceptemailsent)
            else:
                self.assertTrue(prize.acceptemailsent)

        for contributor in prizeContributors:
            acceptedPrizes, deniedPrizes = contributorPrizes[contributor]
            contributorMail = post_office.models.Email.objects.filter(
                to=contributor.email
            )
            if len(acceptedPrizes) == 0 and len(deniedPrizes) == 0:
                self.assertEqual(0, contributorMail.count())
            else:
                self.assertEqual(1, contributorMail.count())
                eventId, handlerId, acceptedIds, deniedIds = self._parseMail(
                    contributorMail[0]
                )
                self.assertEqual(self.event.id, eventId)
                self.assertEqual(contributor.id, handlerId)
                self.assertEqual(len(acceptedPrizes), len(acceptedIds))
                self.assertEqual(len(deniedPrizes), len(deniedIds))
                for prize in acceptedPrizes:
                    self.assertTrue(prize.id in acceptedIds)
                for prize in deniedPrizes:
                    self.assertTrue(prize.id in deniedIds)


class TestAutomailPrizeWinnerAcceptNotifications(TransactionTestCase):
    testTemplateContent = """
        EVENT:{{ event.id }}
        HANDLERID:{{ handler.id }}
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
            self.rand, num_runs=20, num_prizes=self.numPrizes, num_donors=self.numDonors
        )
        self.templateEmail = post_office.models.EmailTemplate.objects.create(
            name='testing_prize_accept_notification',
            description='',
            subject='A Test',
            content=self.testTemplateContent,
        )
        self.sender = 'nobody@nowhere.com'

    def _parseMail(self, mail):
        contents = util.parse_test_mail(mail)
        event = int(contents['event'][0])
        handlerId = int(contents['handlerid'][0])
        prizeWins = [int(x) for x in contents.get('prizewinner', [])]
        reply = contents['reply'][0]
        return event, handlerId, prizeWins, reply

    def testAutomail(self):
        models.Prize.objects.update(state='ACCEPTED')
        prizeContributors = []

        for i in range(0, 10):
            prizeContributors.append(
                AuthUser.objects.create(
                    username='u' + str(i),
                    email='u' + str(i) + '@email.com',
                    is_active=True,
                )
            )

        prizes = models.Prize.objects.all()
        donors = models.Donor.objects.all()
        contributorPrizeWinners = {}

        for contributor in prizeContributors:
            contributorPrizeWinners[contributor] = []

        for prize in prizes:
            prize.handler = self.rand.choice(prizeContributors)
            prize.save()
            prizeWinner = models.PrizeWinner.objects.create(
                winner=self.rand.choice(donors),
                prize=prize,
                acceptcount=1,
                pendingcount=0,
                emailsent=True,
                acceptemailsentcount=0,
            )
            contributorPrizeWinners[prize.handler].append(prizeWinner)

        winnerList = reduce(lambda x, y: x + y, contributorPrizeWinners.values(), [])
        self.assertSetEqual(
            set(prizemail.prizes_with_winner_accept_email_pending(self.event)),
            set(winnerList),
        )

        prizemail.automail_winner_accepted_prize(
            self.event, winnerList, self.templateEmail, sender=self.sender
        )

        for contributor in prizeContributors:
            prizeWinners = contributorPrizeWinners[contributor]
            contributorMail = post_office.models.Email.objects.filter(
                to=contributor.email
            )
            if len(prizeWinners) == 0:
                self.assertEqual(0, contributorMail.count())
            else:
                self.assertEqual(1, contributorMail.count())
                eventId, handlerId, mailedPrizeWinnerIds, reply = self._parseMail(
                    contributorMail[0]
                )
                self.assertEqual(self.event.id, eventId)
                self.assertEqual(contributor.id, handlerId)
                self.assertEqual(len(mailedPrizeWinnerIds), len(prizeWinners))
                for prizeWinner in prizeWinners:
                    self.assertTrue(prizeWinner.id in mailedPrizeWinnerIds)
                    self.assertEqual(
                        prizeWinner.acceptemailsentcount, prizeWinner.acceptcount
                    )
                self.assertEqual(self.sender, reply)


class TestAutomailPrizesShipped(TransactionTestCase):
    testTemplateContent = """
        EVENT:{{ event.id }}
        WINNER:{{ winner.id }}
        {% for prizeWin in prize_wins %}
            PRIZEWINNER:{{ prizeWin.id }}
            {% if prizeWin.prize.key_code %}KEY: {{ prizeWin.prizekey.key }}{% endif %}
        {% endfor %}
        REPLY:{{ reply_address }}
        """

    def setUp(self):
        self.rand = random.Random(None)
        self.numDonors = 20
        self.numPrizes = 40
        self.event = randgen.build_random_event(
            self.rand, num_runs=20, num_prizes=self.numPrizes, num_donors=self.numDonors
        )
        for prize in self.rand.sample(
            list(self.event.prize_set.all()), self.numPrizes // 10
        ):
            prize.key_code = True
            prize.save()
            randgen.generate_prize_key(self.rand, prize=prize).save()
        self.templateEmail = post_office.models.EmailTemplate.objects.create(
            name='testing_prize_shipping_notification',
            description='',
            subject='A Test',
            content=self.testTemplateContent,
        )
        self.sender = 'nobody@nowhere.com'

    def _parseMail(self, mail):
        contents = util.parse_test_mail(mail)
        event = int(contents['event'][0])
        winnerId = int(contents['winner'][0])
        prizeWins = [int(x) for x in contents.get('prizewinner', [])]
        keys = [x.strip() for x in contents.get('key', [])]
        reply = contents['reply'][0]
        return event, winnerId, prizeWins, keys, reply

    def testAutoMail(self):
        models.Prize.objects.update(state='ACCEPTED')
        prizes = models.Prize.objects.all()
        donors = models.Donor.objects.all()
        winningDonors = {}

        for donor in donors:
            winningDonors[donor] = []

        for prize in prizes:
            if self.rand.getrandbits(1) == 0:
                prizeWinner = models.PrizeWinner.objects.create(
                    winner=self.rand.choice(donors),
                    prize=prize,
                    acceptcount=1,
                    pendingcount=0,
                    emailsent=True,
                    acceptemailsentcount=1,
                    shippingstate='SHIPPED',
                    shippingemailsent=False,
                )
                if prize.key_code:
                    key = models.PrizeKey.objects.get(prize=prize)
                    key.prize_winner = prizeWinner
                    key.save()
                winningDonors[prizeWinner.winner].append(prizeWinner)

        winnerList = sum(winningDonors.values(), [])
        self.assertSetEqual(
            set(prizemail.prizes_with_shipping_email_pending(self.event)),
            set(winnerList),
        )

        prizemail.automail_shipping_email_notifications(
            self.event, winnerList, self.templateEmail, sender=self.sender
        )

        for winner in winningDonors:
            prizeWinners = winningDonors[winner]
            winnerMail = post_office.models.Email.objects.filter(to=winner.email)

            if len(prizeWinners) == 0:
                self.assertEqual(0, winnerMail.count())
            else:
                self.assertEqual(1, winnerMail.count())
                eventId, winnerId, mailedPrizeWinnerIds, keys, reply = self._parseMail(
                    winnerMail[0]
                )
                self.assertEqual(self.event.id, eventId)
                self.assertEqual(winner.id, winnerId)
                self.assertEqual(len(mailedPrizeWinnerIds), len(prizeWinners))
                for prizeWinner in prizeWinners:
                    self.assertIn(prizeWinner.id, mailedPrizeWinnerIds)
                    self.assertTrue(prizeWinner.shippingemailsent)
                    if prizeWinner.prize.key_code:
                        self.assertIn(prizeWinner.prizekey.key, keys)
                self.assertEqual(self.sender, reply)
