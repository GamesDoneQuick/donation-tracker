import tracker.tests.util as test_util
import random

from django.test import TransactionTestCase
from django.contrib.auth import get_user_model

import post_office.models

import tracker.models as models
import tracker.randgen as randgen
import tracker.prizemail as prizemail
from functools import reduce

AuthUser = get_user_model()


class TestAutomailPrizeWinners(TransactionTestCase):
    email_template = """
  EVENT:{{ event.id }}
  WINNER:{{ winner.id }}
  WINNER_CONTACT_NAME:{{ winner.contact_name }}
  {% for prize_winner in prize_wins %}
    PRIZE: {{ prize_winner.prize.id }}
  {% endfor %}
  """

    def setUp(self):
        self.rand = random.Random(None)
        self.num_donors = 60
        self.num_prizes = 40
        self.event = randgen.build_random_event(
            self.rand,
            num_runs=20,
            num_prizes=self.num_prizes,
            num_donors=self.num_donors,
        )
        self.template_email = post_office.models.EmailTemplate.objects.create(
            name='testing_prize_winner_notification',
            description='',
            subject='You Win!',
            content=self.email_template,
        )

    def _parse_mail(self, mail):
        contents = test_util.parse_test_mail(mail)
        event = int(contents['event'][0])
        winner = int(contents['winner'][0])
        contact_name = contents['winner_contact_name'][0]
        prizes = [int(p) for p in contents.get('prize', [])]
        return event, winner, contact_name, prizes

    def test_auto_mail(self):
        models.Prize.objects.update(state='ACCEPTED')
        donors = list(models.Donor.objects.all())
        prizes = list(models.Prize.objects.all())
        full_winner_list = []
        donor_wins = {}
        for prize in prizes:
            if self.rand.getrandbits(1) == 0:
                winners = []
                while len(winners) < prize.maxwinners:
                    d = donors[self.rand.randrange(len(donors))]
                    if d not in winners:
                        winners.append(d)
                for winner in winners:
                    full_winner_list.append(
                        models.PrizeWinner.objects.create(
                            winner=winner, prize=prize, pendingcount=1
                        )
                    )
                    donor_prize_list = donor_wins.get(winner.id, None)
                    if donor_prize_list is None:
                        donor_prize_list = []
                    donor_wins[winner.id] = donor_prize_list
                    donor_prize_list.append(prize)

        self.assertSetEqual(
            {pw.id for pw in prizemail.prize_winners_with_email_pending(self.event)},
            {pw.id for pw in full_winner_list},
        )
        prizemail.automail_prize_winners(
            self.event,
            full_winner_list,
            self.template_email,
            sender='nobody@nowhere.com',
        )

        for prize_winner in full_winner_list:
            self.assertTrue(prize_winner.emailsent)
        for donor in donors:
            won_prizes = donor_wins.get(donor.id, [])
            donor_mail = post_office.models.Email.objects.filter(to=donor.email)
            if len(won_prizes) == 0:
                self.assertEqual(0, donor_mail.count())
            else:
                self.assertEqual(1, donor_mail.count())
                event_id, winner_id, contact_name, prize_ids = self._parse_mail(
                    donor_mail[0]
                )
                self.assertEqual(self.event.id, event_id)
                self.assertEqual(donor.id, winner_id)
                self.assertEqual(donor.contact_name(), contact_name)
                self.assertEqual(len(won_prizes), len(prize_ids))
                for prize in won_prizes:
                    self.assertTrue(prize.id in prize_ids)


class TestAutomailPrizeContributors(TransactionTestCase):
    test_template_content = """
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
        self.num_donors = 10
        self.num_prizes = 40
        self.event = randgen.build_random_event(
            self.rand,
            num_runs=20,
            num_prizes=self.num_prizes,
            num_donors=self.num_donors,
        )
        self.template_email = post_office.models.EmailTemplate.objects.create(
            name='testing_prize_submission_response',
            description='',
            subject='A Test',
            content=self.test_template_content,
        )

    def _parse_mail(self, mail):
        contents = test_util.parse_test_mail(mail)
        event = int(contents['event'][0])
        handler_id = int(contents['handlerid'][0])
        accepted = list([int(x) for x in contents.get('accepted', [])])
        denied = list([int(x) for x in contents.get('denied', [])])
        return event, handler_id, accepted, denied

    def test_auto_mail(self):
        prize_contributors = []
        for i in range(0, 10):
            prize_contributors.append(
                AuthUser.objects.create(
                    username='u' + str(i),
                    email='u' + str(i) + '@email.com',
                    is_active=True,
                )
            )
        prizes = models.Prize.objects.all()
        accept_count = 0
        deny_count = 0
        pending_count = 0
        contributor_prizes = {}
        for contributor in prize_contributors:
            contributor_prizes[contributor] = ([], [])
        for prize in prizes:
            prize.handler = self.rand.choice(prize_contributors)
            pick_val = self.rand.randrange(3)
            if pick_val == 0:
                prize.state = 'ACCEPTED'
                accept_count += 1
                contributor_prizes[prize.handler][0].append(prize)
            elif pick_val == 1:
                prize.state = 'DENIED'
                deny_count += 1
                contributor_prizes[prize.handler][1].append(prize)
            else:
                prize.state = 'PENDING'
                pending_count += 1
            prize.save()

        pending_prizes = reduce(
            lambda x, y: x + y[0] + y[1], list(contributor_prizes.values()), []
        )
        self.assertSetEqual(
            set(prizemail.prizes_with_submission_email_pending(self.event)),
            set(pending_prizes),
        )
        prizemail.automail_prize_contributors(
            self.event, pending_prizes, self.template_email, sender='nobody@nowhere.com'
        )

        for prize in models.Prize.objects.all():
            if prize.state == 'PENDING':
                self.assertFalse(prize.acceptemailsent)
            else:
                self.assertTrue(prize.acceptemailsent)

        for contributor in prize_contributors:
            accepted_prizes, denied_prizes = contributor_prizes[contributor]
            contributor_mail = post_office.models.Email.objects.filter(
                to=contributor.email
            )
            if len(accepted_prizes) == 0 and len(denied_prizes) == 0:
                self.assertEqual(0, contributor_mail.count())
            else:
                self.assertEqual(1, contributor_mail.count())
                event_id, handler_id, accepted_ids, denied_ids = self._parse_mail(
                    contributor_mail[0]
                )
                self.assertEqual(self.event.id, event_id)
                self.assertEqual(contributor.id, handler_id)
                self.assertEqual(len(accepted_prizes), len(accepted_ids))
                self.assertEqual(len(denied_prizes), len(denied_ids))
                for prize in accepted_prizes:
                    self.assertTrue(prize.id in accepted_ids)
                for prize in denied_prizes:
                    self.assertTrue(prize.id in denied_ids)


class TestAutomailPrizeWinnerAcceptNotifications(TransactionTestCase):
    test_template_content = """
        EVENT:{{ event.id }}
        HANDLERID:{{ handler.id }}
        {% for prizeWin in prize_wins %}
            PRIZEWINNER:{{ prizeWin.id }}
        {% endfor %}
        REPLY:{{ reply_address }}
        """

    def setUp(self):
        self.rand = random.Random(None)
        self.num_donors = 20
        self.num_prizes = 30
        self.event = randgen.build_random_event(
            self.rand,
            num_runs=20,
            num_prizes=self.num_prizes,
            num_donors=self.num_donors,
        )
        self.template_email = post_office.models.EmailTemplate.objects.create(
            name='testing_prize_accept_notification',
            description='',
            subject='A Test',
            content=self.test_template_content,
        )
        self.sender = 'nobody@nowhere.com'

    def _parse_mail(self, mail):
        contents = test_util.parse_test_mail(mail)
        event = int(contents['event'][0])
        handler_id = int(contents['handlerid'][0])
        prize_wins = list([int(x) for x in contents.get('prizewinner', [])])
        reply = contents['reply'][0]
        return event, handler_id, prize_wins, reply

    def test_automail(self):
        models.Prize.objects.update(state='ACCEPTED')
        prize_contributors = []

        for i in range(0, 10):
            prize_contributors.append(
                AuthUser.objects.create(
                    username='u' + str(i),
                    email='u' + str(i) + '@email.com',
                    is_active=True,
                )
            )

        prizes = models.Prize.objects.all()
        donors = models.Donor.objects.all()
        contributor_prize_winners = {}

        for contributor in prize_contributors:
            contributor_prize_winners[contributor] = []

        for prize in prizes:
            prize.handler = self.rand.choice(prize_contributors)
            prize.save()
            prize_winner = models.PrizeWinner.objects.create(
                winner=self.rand.choice(donors),
                prize=prize,
                acceptcount=1,
                pendingcount=0,
                emailsent=True,
                acceptemailsentcount=0,
            )
            contributor_prize_winners[prize.handler].append(prize_winner)

        winner_list = reduce(
            lambda x, y: x + y, list(contributor_prize_winners.values()), []
        )
        self.assertSetEqual(
            set(prizemail.prizes_with_winner_accept_email_pending(self.event)),
            set(winner_list),
        )

        prizemail.automail_winner_accepted_prize(
            self.event, winner_list, self.template_email, sender=self.sender
        )

        for contributor in prize_contributors:
            prize_winners = contributor_prize_winners[contributor]
            contributor_mail = post_office.models.Email.objects.filter(
                to=contributor.email
            )
            if len(prize_winners) == 0:
                self.assertEqual(0, contributor_mail.count())
            else:
                self.assertEqual(1, contributor_mail.count())
                event_id, handler_id, mailed_prize_winner_ids, reply = self._parse_mail(
                    contributor_mail[0]
                )
                self.assertEqual(self.event.id, event_id)
                self.assertEqual(contributor.id, handler_id)
                self.assertEqual(len(mailed_prize_winner_ids), len(prize_winners))
                for prize_winner in prize_winners:
                    self.assertTrue(prize_winner.id in mailed_prize_winner_ids)
                    self.assertEqual(
                        prize_winner.acceptemailsentcount, prize_winner.acceptcount
                    )
                self.assertEqual(self.sender, reply)


class TestAutomailPrizesShipped(TransactionTestCase):
    test_template_content = """
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
        self.num_donors = 20
        self.num_prizes = 40
        self.event = randgen.build_random_event(
            self.rand,
            num_runs=20,
            num_prizes=self.num_prizes,
            num_donors=self.num_donors,
        )
        for prize in self.rand.sample(
            list(self.event.prize_set.all()), self.num_prizes // 10
        ):
            prize.key_code = True
            prize.save()
            randgen.generate_prize_key(self.rand, prize=prize).save()
        self.template_email = post_office.models.EmailTemplate.objects.create(
            name='testing_prize_shipping_notification',
            description='',
            subject='A Test',
            content=self.test_template_content,
        )
        self.sender = 'nobody@nowhere.com'

    def _parse_mail(self, mail):
        contents = test_util.parse_test_mail(mail)
        event = int(contents['event'][0])
        winner_id = int(contents['winner'][0])
        prize_wins = [int(x) for x in contents.get('prizewinner', [])]
        keys = [x.strip() for x in contents.get('key', [])]
        reply = contents['reply'][0]
        return event, winner_id, prize_wins, keys, reply

    def test_auto_mail(self):
        models.Prize.objects.update(state='ACCEPTED')
        prizes = models.Prize.objects.all()
        donors = models.Donor.objects.all()
        winning_donors = {}

        for donor in donors:
            winning_donors[donor] = []

        for prize in prizes:
            if self.rand.getrandbits(1) == 0:
                prize_winner = models.PrizeWinner.objects.create(
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
                    key.prize_winner = prize_winner
                    key.save()
                winning_donors[prize_winner.winner].append(prize_winner)

        winner_list = sum(list(winning_donors.values()), [])
        self.assertSetEqual(
            set(prizemail.prizes_with_shipping_email_pending(self.event)),
            set(winner_list),
        )

        prizemail.automail_shipping_email_notifications(
            self.event, winner_list, self.template_email, sender=self.sender
        )

        for winner in winning_donors:
            prize_winners = winning_donors[winner]
            winner_mail = post_office.models.Email.objects.filter(to=winner.email)

            if len(prize_winners) == 0:
                self.assertEqual(0, winner_mail.count())
            else:
                self.assertEqual(1, winner_mail.count())
                (
                    event_id,
                    winner_id,
                    mailed_prize_winner_ids,
                    keys,
                    reply,
                ) = self._parse_mail(winner_mail[0])
                self.assertEqual(self.event.id, event_id)
                self.assertEqual(winner.id, winner_id)
                self.assertEqual(len(mailed_prize_winner_ids), len(prize_winners))
                for prize_winner in prize_winners:
                    self.assertIn(prize_winner.id, mailed_prize_winner_ids)
                    self.assertTrue(prize_winner.shippingemailsent)
                    if prize_winner.prize.key_code:
                        self.assertIn(prize_winner.prizekey.key, keys)
                self.assertEqual(self.sender, reply)
