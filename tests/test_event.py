import datetime
import io
import json
import random
import zoneinfo

import post_office.models
from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from tracker import models, settings
from tracker.util import make_rand, utcnow

from . import randgen
from .util import long_ago_noon, parse_csv_response, today_noon, tomorrow_noon


class TestEvent(TestCase):
    def setUp(self):
        self.rand = make_rand()
        self.event = models.Event.objects.create(datetime=today_noon, short='test')
        self.run = models.SpeedRun.objects.create(
            event=self.event,
            starttime=today_noon,
            order=0,
            run_time='00:01:00',
            setup_time='00:01:00',
        )
        randgen.generate_donors(self.rand, 1)

    def test_update_first_run_if_event_time_changes(self):
        self.event.datetime = tomorrow_noon
        self.event.save()
        self.run.refresh_from_db()
        self.assertEqual(self.run.starttime, self.event.datetime)

        self.event.datetime = long_ago_noon
        self.event.save()
        self.run.refresh_from_db()
        self.assertEqual(self.run.starttime, self.event.datetime)

    def test_approve_flagged_donations_with_one_step(self):
        donation = randgen.generate_donation(self.rand, readstate='FLAGGED')
        donation.save()

        self.assertEqual(
            donation.readstate, 'READY', msg='Donation did not fix readstate when saved'
        )

        self.event.use_one_step_screening = False
        self.event.save()

        # neither side of this interaction should change from FLAGGED to READY
        donation.refresh_from_db()
        donation.readstate = 'FLAGGED'
        donation.save()
        self.event.save()
        donation.refresh_from_db()

        self.assertEqual(
            donation.readstate,
            'FLAGGED',
            msg='Donation should not have fixed readstate when saved',
        )

        self.event.use_one_step_screening = True
        self.event.save()

        donation.refresh_from_db()

        self.assertEqual(
            donation.readstate,
            'READY',
            msg='Event did not fix attached Donation readstates when saved',
        )

    def test_manager_current(self):
        with self.subTest('custom timestamp'):
            self.assertEqual(
                models.Event.objects.current(
                    today_noon + datetime.timedelta(seconds=30)
                ),
                self.event,
            )
            self.assertIs(
                models.Event.objects.current(
                    today_noon + datetime.timedelta(seconds=-30)
                ),
                None,
            )
            self.assertIs(
                models.Event.objects.current(
                    today_noon + datetime.timedelta(seconds=150)
                ),
                None,
            )

        with self.subTest('now'):
            self.event.datetime = utcnow()
            self.event.save()
            self.assertEqual(models.Event.objects.current(), self.event)

        with self.subTest('overlap'):
            self.event.datetime = today_noon
            self.event.save()
            overlap_event = models.Event.objects.create(
                datetime=today_noon, short='test2'
            )
            models.SpeedRun.objects.create(
                event=overlap_event,
                order=0,
                run_time='00:01:00',
                setup_time='00:01:00',
            )
            with self.assertLogs('tracker.models.event', 'WARNING'):
                self.assertIs(
                    models.Event.objects.current(
                        today_noon + datetime.timedelta(seconds=30)
                    ),
                    None,
                )

    def test_manager_next(self):
        with self.subTest('custom timestamp'):
            self.assertIs(
                models.Event.objects.next(today_noon),
                None,
            )
            self.assertEqual(
                models.Event.objects.next(today_noon + datetime.timedelta(seconds=-1)),
                self.event,
            )

        with self.subTest('multiple events'):
            prev_event = models.Event.objects.create(
                datetime=today_noon - datetime.timedelta(hours=1),
                short='test2',
            )
            next_event = models.Event.objects.create(
                datetime=today_noon + datetime.timedelta(hours=1),
                short='test4',
            )
            self.assertEqual(
                models.Event.objects.next(
                    prev_event.datetime - datetime.timedelta(seconds=1)
                ),
                prev_event,
            )
            self.assertEqual(models.Event.objects.next(prev_event.datetime), self.event)
            self.assertEqual(models.Event.objects.next(self.event.datetime), next_event)
            self.assertIs(models.Event.objects.next(next_event.datetime), None)

        with self.subTest('now'):
            self.event.datetime = utcnow() + datetime.timedelta(seconds=30)
            self.event.save()
            self.assertEqual(models.Event.objects.next(), self.event)

    def test_prev_and_next(self):
        events = []
        models.SpeedRun.objects.all().delete()
        models.Event.objects.all().delete()
        for i in range(5):
            events.append(
                models.Event.objects.create(
                    name=f'Event #{i}',
                    short=f'event{i}',
                    datetime=today_noon + datetime.timedelta(days=i + 5),
                )
            )
        for i, e in enumerate(events):
            e.refresh_from_db()
            if i > 0:
                with self.subTest(f'{e.name} prev'):
                    self.assertEqual(e.prev(), events[i - 1])
            else:
                with self.subTest(f'{e.name} prev'):
                    self.assertIs(e.prev(), None)
            if i < 4:
                with self.subTest(f'{e.name} next'):
                    self.assertEqual(e.next(), events[i + 1])
            else:
                with self.subTest(f'{e.name} next'):
                    self.assertIs(e.next(), None)


class TestEventManager(TransactionTestCase):
    def setUp(self):
        self.rand = random.Random()
        self.event = models.Event.objects.create(datetime=today_noon)
        self.completed_donations = randgen.generate_donations(
            self.rand,
            self.event,
            5,
            start_time=self.event.datetime,
            end_time=self.event.datetime + datetime.timedelta(hours=1),
        )
        self.pending_donations = randgen.generate_donations(
            self.rand,
            self.event,
            2,
            start_time=self.event.datetime,
            end_time=self.event.datetime + datetime.timedelta(hours=1),
            domain='PAYPAL',
            transactionstate='PENDING',
        )
        self.manager = models.Event.objects

    def test_donation_count_annotation(self):
        manager = models.Event.objects.with_annotations()
        event = manager.get(pk=self.event.pk)
        self.assertEqual(event.donation_count, len(self.completed_donations))

    def test_amount_annotation(self):
        manager = models.Event.objects.with_annotations()
        event = manager.get(pk=self.event.pk)
        total_amount = sum(donation.amount for donation in self.completed_donations)
        self.assertAlmostEqual(event.amount, total_amount)


class TestEventViews(TransactionTestCase):
    def setUp(self):
        self.event = models.Event.objects.create(
            datetime=today_noon, short='short', name='Short'
        )

    @override_settings(TRACKER_LOGO='example-logo.png')
    def test_main_index(self):
        models.Donation.objects.create(
            event=self.event, amount=5, transactionstate='COMPLETED'
        )
        models.Donation.objects.create(
            event=self.event, amount=10, transactionstate='COMPLETED'
        )
        response = self.client.get(reverse('tracker:index_all'))
        self.assertContains(response, 'All Events')
        self.assertContains(response, 'example-logo.png')
        self.assertContains(response, '$15.00 (2)', 1)
        self.assertContains(response, '$10.00', 1)
        self.assertContains(response, '$7.50', 2)

    def test_json_with_no_donations(self):
        response = self.client.get(
            reverse('tracker:index', args=(self.event.id,)), data={'json': ''}
        )
        self.assertEqual(
            json.loads(response.content),
            {
                'count': {
                    'bids': 0,
                    # 'donors': 0,
                    'milestones': 0,
                    'prizes': 0,
                    'runs': 0,
                },
                'agg': {
                    'amount': 0.0,
                    'avg': 0.0,
                    'count': 0,
                    'max': 0.0,
                    'median': 0.0,
                },
            },
        )

    def test_json_with_only_pending_donations(self):
        models.Donation.objects.create(event=self.event, amount=5, domain='PAYPAL')
        response = self.client.get(
            reverse('tracker:index', args=(self.event.id,)), data={'json': ''}
        )
        self.assertEqual(
            json.loads(response.content),
            {
                'count': {
                    'bids': 0,
                    # 'donors': 0,
                    'milestones': 0,
                    'prizes': 0,
                    'runs': 0,
                },
                'agg': {
                    'amount': 0.0,
                    'avg': 0.0,
                    'count': 0,
                    'max': 0.0,
                    'median': 0.0,
                },
            },
        )

    def test_json_with_cleared_donations(self):
        models.Donation.objects.create(
            event=self.event, amount=5, transactionstate='COMPLETED'
        )
        models.Donation.objects.create(
            event=self.event, amount=10, transactionstate='COMPLETED'
        )
        response = self.client.get(
            reverse('tracker:index', args=(self.event.id,)), data={'json': ''}
        )
        self.assertEqual(
            json.loads(response.content),
            {
                'count': {
                    'bids': 0,
                    # 'donors': 0,
                    'milestones': 0,
                    'prizes': 0,
                    'runs': 0,
                },
                'agg': {
                    'amount': 15.0,
                    'avg': 7.5,
                    'count': 2,
                    'max': 10.0,
                    'median': 7.5,
                },
            },
        )


class TestEventAdmin(TestCase):
    def setUp(self):
        self.super_user = User.objects.create_superuser(
            'admin', 'admin@example.com', 'password'
        )
        timezone = zoneinfo.ZoneInfo(settings.TIME_ZONE)
        self.event = models.Event.objects.create(
            datetime=today_noon,
            timezone=timezone,
            name='test event',
            short='test',
        )
        self.rand = random.Random(None)
        self.client.force_login(self.super_user)

    def test_event_admin(self):
        response = self.client.get(reverse('admin:tracker_event_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_event_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_event_change', args=(self.event.id,))
        )
        self.assertEqual(response.status_code, 200)

    def test_security(self):
        self.staff = User.objects.create(username='staff', is_staff=True)
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse('admin:send_volunteer_emails', args=(self.event.id,))
        )
        self.assertEqual(response.status_code, 403)
        self.staff.user_permissions.add(
            Permission.objects.get(name='Can change user'),
        )
        response = self.client.get(
            reverse('admin:send_volunteer_emails', args=(self.event.id,))
        )
        self.assertEqual(response.status_code, 200)

    def test_send_volunteer_emails(self):
        self.template = post_office.models.EmailTemplate.objects.create(
            name='Test Template',
            content="""
{% if is_head %}
    {{ user }} is a head donation screener.
{% elif is_host %}
    {{ user }} is a host.
{% elif is_schedule %}
    {{ user }} is a schedule viewer.
{% else %}
    {{ user }} is a donation screener.
{% endif %}""",
        )
        response = self.client.get(
            reverse('admin:send_volunteer_emails', args=(self.event.id,))
        )
        self.assertEqual(response.status_code, 200)
        volunteers = io.StringIO(
            """position,name,username,email
Host,Jesse Doe,Garden,jessedoe@example.com
Head Donations,John Doe,Ribs,johndoe@example.com
Schedule,Jack Doe,Snakes,jackdoe@example.com
Donations,Jane Doe,Apples,janedoe@example.com
Donations,Add Min,SHOULD_NOT_CHANGE,admin@example.com
Donations,,invalid,invalid.email.com
Donations,,,blank@example.com
"""
        )
        emails = post_office.models.Email.objects.count()
        users = User.objects.count()
        response = self.client.post(
            reverse('admin:send_volunteer_emails', args=(self.event.id,)),
            data={
                'template': self.template.id,
                'sender': 'root@localhost',
                'volunteers': volunteers,
            },
        )
        self.assertRedirects(response, reverse('admin:tracker_event_changelist'))
        self.assertEqual(
            # emails + 6, # FIXME? why did this change
            emails + 6,
            post_office.models.Email.objects.count(),
            'Did not send six emails',
        )
        self.assertEqual(users + 5, User.objects.count(), 'Did not add five users')
        self.super_user.refresh_from_db()
        self.assertTrue(
            Group.objects.get(name='Bid Admin')
            in User.objects.get(email='johndoe@example.com').groups.all(),
            'john should belong to Bid Admin',
        )
        self.assertFalse(
            Group.objects.get(name='Bid Tracker')
            in User.objects.get(email='johndoe@example.com').groups.all(),
            'john should not belong to Bid Tracker',
        )
        self.assertIn(
            'Ribs is a head donation screener.',
            post_office.models.Email.objects.get(to='johndoe@example.com').message,
            "john's email was not tagged as head donations",
        )
        self.assertTrue(
            Group.objects.get(name='Bid Tracker')
            in User.objects.get(email='jessedoe@example.com').groups.all(),
            'jesse should belong to Bid Tracker',
        )
        self.assertFalse(
            Group.objects.get(name='Bid Admin')
            in User.objects.get(email='jessedoe@example.com').groups.all(),
            'jesse should not belong to Bid Admin',
        )
        self.assertIn(
            'Garden is a host.',
            post_office.models.Email.objects.get(to='jessedoe@example.com').message,
            "jesse's email was not tagged as host",
        )
        self.assertIn(
            'Snakes is a schedule viewer.',
            post_office.models.Email.objects.get(to='jackdoe@example.com').message,
            "jack's email was not tagged as a schedule viewer",
        )
        self.assertTrue(
            Group.objects.get(name='Schedule Viewer')
            in User.objects.get(email='jackdoe@example.com').groups.all(),
            'jack should belong to Schedule Viewer',
        )
        self.assertTrue(
            Group.objects.get(name='Bid Tracker')
            in User.objects.get(email='janedoe@example.com').groups.all(),
            'jane should belong to Bid Tracker',
        )
        self.assertFalse(
            Group.objects.get(name='Bid Admin')
            in User.objects.get(email='janedoe@example.com').groups.all(),
            'jane should not belong to Bid Admin',
        )
        self.assertIn(
            'Apples is a donation screener.',
            post_office.models.Email.objects.get(to='janedoe@example.com').message,
            "jane's email was not tagged as donations",
        )
        self.assertEqual(
            self.super_user.username,
            'admin',
            'Should not have changed existing username',
        )
        self.assertFalse(
            User.objects.filter(username='invalid').exists(),
            'Should not have created user with invalid email',
        )
        self.assertEqual(
            User.objects.get(email='blank@example.com').username,
            'blank@example.com',
            'Should have created user with email as username when entry was blank',
        )

        minimal = io.StringIO(
            """email
minimal@example.com
"""
        )
        emails = post_office.models.Email.objects.count()
        users = User.objects.count()
        response = self.client.post(
            reverse('admin:send_volunteer_emails', args=(self.event.id,)),
            data={
                'template': self.template.id,
                'sender': 'root@localhost',
                'volunteers': minimal,
            },
        )
        self.assertRedirects(response, reverse('admin:tracker_event_changelist'))
        self.assertEqual(
            emails + 1,
            post_office.models.Email.objects.count(),
            'Did not send one email',
        )
        self.assertEqual(users + 1, User.objects.count(), 'Did not add one user')
        self.assertTrue(
            Group.objects.get(name='Bid Tracker')
            in User.objects.get(email='minimal@example.com').groups.all(),
            'minimal should belong to Bid Tracker',
        )
        self.assertFalse(
            Group.objects.get(name='Bid Admin')
            in User.objects.get(email='minimal@example.com').groups.all(),
            'minimal should not belong to Bid Admin',
        )
        self.assertIn(
            'minimal@example.com is a donation screener.',
            post_office.models.Email.objects.get(to='minimal@example.com').message,
            "minimal's email was not tagged as donations",
        )

    def test_event_donor_report(self):
        donor1 = randgen.generate_donor(self.rand, visibility='ANON')
        donor1.save()
        donation1 = randgen.generate_donation(self.rand, donor=donor1, event=self.event)
        donation1.save()
        donor2 = randgen.generate_donor(self.rand, visibility='ANON')
        donor2.save()
        donation2 = randgen.generate_donation(self.rand, donor=donor2, event=self.event)
        donation2.save()
        donor3 = randgen.generate_donor(self.rand, visibility='FULL')
        donor3.save()
        donation3 = randgen.generate_donation(self.rand, donor=donor3, event=self.event)
        donation3.save()
        donation4 = randgen.generate_donation(
            self.rand,
            donor=donor3,
            event=self.event,
            domain='PAYPAL',
            transactionstate='PENDING',
        )
        donation4.save()
        resp = self.client.post(
            reverse('admin:tracker_event_changelist'),
            {'action': 'donor_report', '_selected_action': [self.event.id]},
        )
        self.assertEqual(resp.status_code, 200)
        lines = parse_csv_response(resp)
        self.assertEqual(len(lines), 3)
        self.assertEqual(
            lines[1],
            ['All Anonymous Donations', str(donation1.amount + donation2.amount), '2'],
        )
        self.assertEqual(lines[2], [donor3.visible_name(), str(donation3.amount), '1'])

    def test_event_run_report(self):
        runs = randgen.generate_runs(self.rand, self.event, 2, ordered=True)
        randgen.generate_runs(self.rand, self.event, 2, ordered=False)
        runs[0].runners.add(*randgen.generate_runners(self.rand, 2))
        runs[1].runners.add(*randgen.generate_runners(self.rand, 1))
        resp = self.client.post(
            reverse('admin:tracker_event_changelist'),
            {'action': 'run_report', '_selected_action': [self.event.id]},
        )
        self.assertEqual(resp.status_code, 200)
        lines = parse_csv_response(resp)
        self.assertEqual(len(lines), 3)

        def line_for(run):
            return [
                str(run),
                run.event.short,
                run.starttime.astimezone(run.event.timezone).isoformat(),
                run.endtime.astimezone(run.event.timezone).isoformat(),
                ','.join(str(r) for r in run.runners.all()),
                ','.join(r.twitter for r in run.runners.all() if r.twitter),
            ]

        self.assertEqual(lines[1], line_for(runs[0]))
        self.assertEqual(lines[2], line_for(runs[1]))

    def test_event_donation_report(self):
        randgen.generate_runs(self.rand, self.event, 5, ordered=True)
        randgen.generate_donors(self.rand, 5)
        donations = randgen.generate_donations(self.rand, self.event, 10)
        randgen.generate_donations(
            self.rand, self.event, 10, transactionstate='PENDING', domain='PAYPAL'
        )
        resp = self.client.post(
            reverse('admin:tracker_event_changelist'),
            {'action': 'donation_report', '_selected_action': [self.event.id]},
        )
        self.assertEqual(resp.status_code, 200)
        lines = parse_csv_response(resp)

        self.assertEqual(len(lines), 11)

        def line_for(donation):
            return [
                donation.donor.visible_name(),
                donation.event.short,
                str(donation.amount),
                donation.timereceived.astimezone(donation.event.timezone).isoformat(),
            ]

        expected = [
            line_for(d)
            for d in sorted(donations, key=lambda d: d.timereceived, reverse=True)
        ]

        for csv_line, expected_line in zip(lines[1:], expected):
            self.assertEqual(csv_line, expected_line)

    def test_event_bid_report(self):
        runs = randgen.generate_runs(self.rand, self.event, 2, ordered=True)
        closed_goal = randgen.generate_bid(
            self.rand, allow_children=False, run=runs[0], state='CLOSED', add_goal=True
        )[0]
        closed_goal.save()
        opened_bid, children = randgen.generate_bid(
            self.rand,
            allow_children=True,
            min_children=5,
            max_children=5,
            max_depth=1,
            run=runs[1],
            state='OPENED',
            add_goal=False,
        )
        randgen.chain_insert_bid(opened_bid, children)
        opened_bid.save()
        hidden_goal = randgen.generate_bid(
            self.rand,
            allow_children=False,
            event=self.event,
            state='HIDDEN',
            add_goal=True,
        )[0]
        hidden_goal.save()
        randgen.generate_donations(
            self.rand,
            self.event,
            50,
            bid_targets_list=[closed_goal] + list(opened_bid.get_children()),
        )
        closed_goal.refresh_from_db()
        opened_bid.refresh_from_db()
        resp = self.client.post(
            reverse('admin:tracker_event_changelist'),
            {'action': 'bid_report', '_selected_action': [self.event.id]},
        )
        self.assertEqual(resp.status_code, 200)
        lines = parse_csv_response(resp)
        self.assertEqual(len(lines), 8)

        def line_for(bid):
            return [
                str(bid.id),
                str(bid),
                bid.event.short,
                str(bid.istarget),
                str(bid.goal) if bid.goal else '',
                str(bid.total),
                str(bid.count),
            ]

        self.assertEqual(lines[1], line_for(closed_goal))
        self.assertEqual(lines[2], line_for(opened_bid))

        expected_children = [
            line_for(bid)
            for bid in sorted(
                opened_bid.get_children(), key=lambda c: c.total, reverse=True
            )
        ]

        for csv_line, expected_line in zip(lines[3:], expected_children):
            self.assertEqual(csv_line, expected_line)

    def test_event_donationbid_report(self):
        randgen.generate_runs(self.rand, self.event, 2, ordered=True)
        closed_goal = randgen.generate_bid(
            self.rand,
            allow_children=False,
            event=self.event,
            state='CLOSED',
            add_goal=True,
        )[0]
        closed_goal.save()
        open_goal = randgen.generate_bid(
            self.rand,
            allow_children=False,
            event=self.event,
            state='OPENED',
            add_goal=True,
        )[0]
        open_goal.save()
        hidden_goal = randgen.generate_bid(
            self.rand,
            allow_children=False,
            event=self.event,
            state='HIDDEN',
            add_goal=True,
        )[0]
        hidden_goal.save()
        randgen.generate_donations(
            self.rand,
            self.event,
            10,
            bid_targets_list=[closed_goal],
            transactionstate='COMPLETED',
        )
        randgen.generate_donations(
            self.rand,
            self.event,
            10,
            bid_targets_list=[closed_goal],
            transactionstate='PENDING',
            domain='PAYPAL',
        )
        randgen.generate_donations(
            self.rand,
            self.event,
            10,
            bid_targets_list=[open_goal],
            transactionstate='COMPLETED',
        )
        randgen.generate_donations(
            self.rand,
            self.event,
            10,
            bid_targets_list=[hidden_goal],
            transactionstate='COMPLETED',
        )
        resp = self.client.post(
            reverse('admin:tracker_event_changelist'),
            {'action': 'donationbid_report', '_selected_action': [self.event.id]},
        )
        self.assertEqual(resp.status_code, 200)
        lines = parse_csv_response(resp)
        self.assertEqual(len(lines), 21)

        def line_for(dbid):
            return [str(dbid.bid_id), str(dbid.amount), str(dbid.donation.timereceived)]

        expected = [
            line_for(dbid)
            for dbid in models.DonationBid.objects.filter(
                bid__state__in=['CLOSED', 'OPENED'],
                donation__transactionstate='COMPLETED',
            ).order_by('donation__timereceived')
        ]

        for csv_line, expected_line in zip(lines[1:], expected):
            self.assertEqual(csv_line, expected_line)

    def test_event_prize_report(self):
        runs = randgen.generate_runs(self.rand, self.event, 2, ordered=True)
        prize = randgen.generate_prize(
            self.rand,
            event=self.event,
            start_run=runs[0],
            end_run=runs[0],
            sum_donations=False,
            min_amount=5,
        )
        prize.save()
        donors = randgen.generate_donors(self.rand, 3)
        randgen.generate_donation(
            self.rand,
            donor=donors[0],
            event=self.event,
            min_time=runs[0].starttime,
            max_time=runs[0].endtime,
            min_amount=prize.minimumbid + 5,
            transactionstate='COMPLETED',
        ).save()
        randgen.generate_donation(
            self.rand,
            donor=donors[1],
            event=self.event,
            min_time=runs[0].starttime,
            max_time=runs[0].endtime,
            min_amount=prize.minimumbid,
            max_amount=prize.minimumbid,
            transactionstate='COMPLETED',
        ).save()
        grandPrize = randgen.generate_prize(
            self.rand,
            event=self.event,
            sum_donations=True,
            min_amount=50,
        )
        grandPrize.save()
        # generate 2 for summation
        randgen.generate_donation(
            self.rand,
            donor=donors[0],
            event=self.event,
            min_time=runs[1].starttime,
            max_time=runs[1].endtime,
            min_amount=grandPrize.minimumbid // 2,
            max_amount=grandPrize.minimumbid // 2,
            transactionstate='COMPLETED',
        ).save()
        randgen.generate_donation(
            self.rand,
            donor=donors[0],
            event=self.event,
            min_time=runs[1].starttime,
            max_time=runs[1].endtime,
            min_amount=grandPrize.minimumbid * 3 // 4,
            max_amount=grandPrize.minimumbid * 3 // 4,
            transactionstate='COMPLETED',
        ).save()
        # also has another donation in
        randgen.generate_donation(
            self.rand,
            donor=donors[1],
            event=self.event,
            min_time=runs[1].starttime,
            max_time=runs[1].endtime,
            min_amount=grandPrize.minimumbid,
            max_amount=grandPrize.minimumbid,
            transactionstate='COMPLETED',
        ).save()
        # only has donation for grand prize
        randgen.generate_donation(
            self.rand,
            donor=donors[2],
            event=self.event,
            # very, very rarely crosses over into the other window unless we nudge it
            min_time=runs[1].starttime + datetime.timedelta(seconds=30),
            max_time=runs[1].endtime,
            min_amount=grandPrize.minimumbid,
            max_amount=grandPrize.minimumbid,
            transactionstate='COMPLETED',
        ).save()

        resp = self.client.post(
            reverse('admin:tracker_event_changelist'),
            {'action': 'prize_report', '_selected_action': [self.event.id]},
        )
        self.assertEqual(resp.status_code, 200)
        lines = parse_csv_response(resp)
        self.assertEqual(len(lines), 3)
        self.assertEqual(
            lines[1],
            [
                'test',
                grandPrize.name,
                '3',  # eligible donors
                '1',  # exact donors
                '',
                '',
            ],
            msg='Grand prize was incorrect',
        )
        self.assertEqual(
            lines[2],
            [
                'test',
                prize.name,
                '2',  # eligible donors
                '1',  # exact donors
                str(runs[0].start_time_utc),
                str(runs[0].end_time_utc),
            ],
            msg='Normal prize was incorrect',
        )

    def test_event_email_report(self):
        randgen.generate_runs(self.rand, self.event, 2, ordered=True)
        donors = randgen.generate_donors(self.rand, 4)
        donors[1].solicitemail = 'OPTIN'
        donors[1].lastname = ''
        donors[1].save()
        donors[2].solicitemail = 'OPTIN'
        donors[2].firstname = ''
        donors[2].lastname = ''
        donors[2].save()
        donors[3].solicitemail = 'OPTIN'
        donors[3].save()
        randgen.generate_donations(self.rand, self.event, 50)

        resp = self.client.post(
            reverse('admin:tracker_event_changelist'),
            {'action': 'email_report', '_selected_action': [self.event.id]},
        )
        self.assertEqual(resp.status_code, 200)
        lines = parse_csv_response(resp)
        self.assertEqual(len(lines), 4)

        def line_for(d):
            if d.firstname:
                if d.lastname:
                    name = u'%s, %s' % (d.lastname, d.firstname)
                else:
                    name = d.firstname
            else:
                name = '(No Name Supplied)'
            return [
                d.email,
                name,
                str(d.visibility == 'ANON'),
                str(d.donation_total),
                str(d.addresscountry or ''),
            ]

        expected = [
            line_for(d)
            for d in models.DonorCache.objects.filter(
                event=self.event,
                donor__solicitemail='OPTIN',
            ).select_related('donor')
        ]

        for csv_line, expected_line in zip(lines[1:], expected):
            self.assertEqual(csv_line, expected_line)

    def test_run_admin(self):
        self.run = models.SpeedRun.objects.create(event=self.event)
        response = self.client.get(reverse('admin:tracker_speedrun_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_speedrun_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_speedrun_change', args=(self.run.id,))
        )
        self.assertEqual(response.status_code, 200)

    def test_talent_admin(self):
        self.runner = models.Talent.objects.create()
        response = self.client.get(reverse('admin:tracker_talent_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_talent_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_talent_change', args=(self.runner.id,))
        )
        self.assertEqual(response.status_code, 200)

    def test_postbackurl_admin(self):
        self.postbackurl = models.PostbackURL.objects.create(event=self.event)
        response = self.client.get(reverse('admin:tracker_postbackurl_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_postbackurl_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_postbackurl_change', args=(self.postbackurl.id,))
        )
        self.assertEqual(response.status_code, 200)
