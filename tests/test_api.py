import datetime
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.core.serializers.json import DjangoJSONEncoder
from django.test import override_settings
from django.urls import reverse

import tracker.models as models
import tracker.views.api
from tracker.serializers import TrackerSerializer

from . import randgen
from .util import APITestCase, today_noon, tomorrow_noon


def format_time(dt):
    return DjangoJSONEncoder().default(dt.astimezone(datetime.timezone.utc))


class TestGeneric(APITestCase):
    """generic cases that could apply to any class, even if they use a specific one for testing purposes"""

    @override_settings(TRACKER_PAGINATION_LIMIT=20)
    def test_search_with_offset_and_limit(self):
        event = randgen.generate_event(self.rand, today_noon)
        event.save()
        randgen.generate_runs(self.rand, event, 5, ordered=True)
        randgen.generate_donors(self.rand, 25)
        randgen.generate_donations(self.rand, event, 50, transactionstate='COMPLETED')
        request = self.factory.get(
            '/api/v1/search',
            dict(type='donation', offset=10, limit=10),
        )
        request.user = self.anonymous_user
        data = self.parseJSON(tracker.views.api.search(request))
        donations = models.Donation.objects.all()
        self.assertEqual(len(data), 10)
        self.assertSetEqual({d['pk'] for d in data}, {d.id for d in donations[10:20]})

        request = self.factory.get(
            '/api/v1/search',
            dict(type='donation', limit=30),
        )
        # bad request if limit is set above server config
        self.parseJSON(tracker.views.api.search(request), status_code=400)

        request = self.factory.get(
            '/api/v1/search',
            dict(type='donation', limit=-1),
        )
        # bad request if limit is negative
        self.parseJSON(tracker.views.api.search(request), status_code=400)

        request = self.factory.get(
            '/api/v1/search',
            dict(type='donation', limit=0),
        )
        # bad request if limit is zero
        self.parseJSON(tracker.views.api.search(request), status_code=400)

        request = self.factory.get(
            '/api/v1/search',
            dict(type='donation', offset=-1),
        )
        # bad request if offset is negative
        self.parseJSON(tracker.views.api.search(request), status_code=400)


class TestSpeedRun(APITestCase):
    model_name = 'Speed Run'

    def setUp(self):
        super().setUp()
        self.blechy = models.Talent.objects.create(name='blechy')
        self.spike = models.Talent.objects.create(name='SpikeVegeta')
        self.run1 = models.SpeedRun.objects.create(
            event=self.event,
            name='Test Run',
            category='test%',
            giantbomb_id=0x5EADBEEF,
            console='NES',
            run_time='0:45:00',
            setup_time='0:05:00',
            release_year=1988,
            description='Foo',
            order=1,
            tech_notes='This run requires an LCD with 0.58ms of lag for a skip late in the game',
            layout='Standard 1',
            coop=True,
        )
        self.run1.commentators.add(self.blechy)
        self.run1.hosts.add(self.spike)
        self.run2 = models.SpeedRun.objects.create(
            event=self.event,
            name='Test Run 2',
            run_time='0:15:00',
            setup_time='0:05:00',
            order=2,
        )
        self.run3 = models.SpeedRun.objects.create(
            event=self.event,
            name='Test Run 3',
            run_time='0:20:00',
            setup_time='0:05:00',
            order=None,
        )
        self.run4 = models.SpeedRun.objects.create(
            event=self.event,
            name='Test Run 4',
            run_time='0:05:00',
            setup_time='0',
            order=3,
        )
        self.runner1 = models.Talent.objects.create(name='trihex')
        self.runner2 = models.Talent.objects.create(name='PJ')
        self.run1.runners.add(self.runner1)
        self.event2 = models.Event.objects.create(
            datetime=tomorrow_noon,
            short='event2',
        )
        self.run5 = models.SpeedRun.objects.create(
            name='Test Run 5',
            run_time='0:05:00',
            setup_time='0',
            order=1,
            event=self.event2,
        )

    @classmethod
    def format_run(cls, run):
        return dict(
            fields=dict(
                anchor_time=run.anchor_time,
                canonical_url=(
                    'http://testserver' + reverse('tracker:run', args=(run.id,))
                ),
                category=run.category,
                commentators=[c.id for c in run.commentators.all()],
                console=run.console,
                coop=run.coop,
                description=run.description,
                display_name=run.display_name,
                endtime=format_time(run.endtime) if run.endtime else run.endtime,
                event=run.event.id,
                giantbomb_id=run.giantbomb_id,
                hosts=[h.id for h in run.hosts.all()],
                name=run.name,
                onsite=run.onsite,
                order=run.order,
                priority_tag=run.priority_tag and run.priority_tag.id,
                public=str(run),
                release_year=run.release_year,
                run_time=run.run_time,
                runners=[runner.id for runner in run.runners.all()],
                setup_time=run.setup_time,
                starttime=(
                    format_time(run.starttime) if run.starttime else run.starttime
                ),
                tags=[t.id for t in run.tags.all()],
                twitch_name=run.twitch_name,
            ),
            model='tracker.speedrun',
            pk=run.id,
        )

    format_model = format_run

    def test_get_single_run(self):
        request = self.factory.get('/api/v1/search', dict(type='run', id=self.run1.id))
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 1)
        self.assertModelPresent(self.run1, data)

    def test_get_event_runs(self):
        request = self.factory.get(
            '/api/v1/search', dict(type='run', event=self.run1.event_id)
        )
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 4)
        self.assertModelPresent(self.run1, data)
        self.assertModelPresent(self.run2, data)
        self.assertModelPresent(self.run3, data)
        self.assertModelPresent(self.run4, data)

    def test_get_starttime_lte(self):
        request = self.factory.get(
            '/api/v1/search',
            dict(type='run', starttime_lte=format_time(self.run2.starttime)),
        )
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 2)
        self.assertModelPresent(self.run1, data)
        self.assertModelPresent(self.run2, data)

    def test_get_starttime_gte(self):
        request = self.factory.get(
            '/api/v1/search',
            dict(type='run', starttime_gte=format_time(self.run2.starttime)),
        )
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 3)
        self.assertModelPresent(self.run2, data)
        self.assertModelPresent(self.run4, data)
        self.assertModelPresent(self.run5, data)

    def test_get_endtime_lte(self):
        request = self.factory.get(
            '/api/v1/search',
            dict(type='run', endtime_lte=format_time(self.run2.endtime)),
        )
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 2)
        self.assertModelPresent(self.run1, data)
        self.assertModelPresent(self.run2, data)

    def test_get_endtime_gte(self):
        request = self.factory.get(
            '/api/v1/search',
            dict(type='run', endtime_gte=format_time(self.run2.endtime)),
        )
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 3)
        self.assertModelPresent(self.run2, data)
        self.assertModelPresent(self.run4, data)
        self.assertModelPresent(self.run5, data)

    def test_tech_notes_without_permission(self):
        request = self.factory.get(
            '/api/v1/search', dict(type='run', id=self.run1.id, tech_notes='')
        )
        request.user = self.anonymous_user
        self.parseJSON(tracker.views.api.search(request), status_code=403)

    def test_tech_notes_with_permission(self):
        request = self.factory.get(
            '/api/v1/search', dict(type='run', id=self.run1.id, tech_notes='')
        )
        request.user = self.user
        self.user.user_permissions.add(
            Permission.objects.get(name='Can view tech notes')
        )
        data = self.parseJSON(tracker.views.api.search(request))
        expected = self.format_run(self.run1)
        expected['fields']['tech_notes'] = self.run1.tech_notes
        expected['fields']['layout'] = self.run1.layout
        self.assertModelPresent(expected, data)


class TestTalent(APITestCase):
    model_name = 'talent'

    def setUp(self):
        super().setUp()
        self.runner1 = models.Talent.objects.create(name='lower')
        self.runner2 = models.Talent.objects.create(name='UPPER')
        self.run1 = models.SpeedRun.objects.create(
            event=self.event, name='Run 1', order=1, run_time='5:00', setup_time='5:00'
        )
        self.run1.runners.add(self.runner1)
        self.run2 = models.SpeedRun.objects.create(
            event=self.event, name='Run 2', order=2, run_time='5:00', setup_time='5:00'
        )
        self.run2.runners.add(self.runner1)

    @classmethod
    def format_talent(cls, runner):
        return dict(
            fields=dict(
                donor=runner.donor.visible_name() if runner.donor else None,
                public=runner.name,
                name=runner.name,
                stream=runner.stream,
                twitter=runner.twitter,
                youtube=runner.youtube,
                platform=runner.platform,
                pronouns=runner.pronouns,
            ),
            model='tracker.talent',
            pk=runner.id,
        )

    def test_name_case_insensitive_search(self):
        request = self.factory.get(
            '/api/v1/search', dict(type='runner', name=self.runner1.name.upper())
        )
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        expected = self.format_talent(self.runner1)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0], expected)

    def test_search_by_event(self):
        request = self.factory.get(
            '/api/v1/search', dict(type='runner', event=self.event.id)
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.search(request))
        expected = self.format_talent(self.runner1)
        # testing both that the other runner does not show up, and that this runner only shows up once
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0], expected)


class TestPrize(APITestCase):
    model_name = 'prize'

    def setUp(self):
        super(TestPrize, self).setUp()

    @classmethod
    def format_prize(cls, prize):
        def add_run_fields(fields, run, prefix):
            dumped_run = TrackerSerializer(models.SpeedRun).serialize([run])[0]
            for key, value in dumped_run['fields'].items():
                if key not in [
                    'canonical_url',
                    'endtime',
                    'name',
                    'starttime',
                    'display_name',
                    'order',
                    'category',
                ]:
                    continue
                try:
                    value = DjangoJSONEncoder().default(value)
                except TypeError:
                    pass
                fields[prefix + '__' + key] = value
            fields[prefix + '__public'] = str(run)

        run_fields = {}
        if prize.startrun:
            add_run_fields(run_fields, prize.startrun, 'startrun')
            add_run_fields(run_fields, prize.endrun, 'endrun')
        draw_time_fields = {}
        if prize.has_draw_time():
            draw_time_fields['start_draw_time'] = cls.encoder.default(
                prize.start_draw_time()
            )
            draw_time_fields['end_draw_time'] = cls.encoder.default(
                prize.end_draw_time()
            )

        return dict(
            fields=dict(
                allowed_prize_countries=[
                    c.id for c in prize.allowed_prize_countries.all()
                ],
                disallowed_prize_regions=[
                    r.id for r in prize.disallowed_prize_regions.all()
                ],
                public=prize.name,
                name=prize.name,
                canonical_url=(reverse('tracker:prize', args=(prize.id,))),
                category=prize.category_id,
                image=prize.image,
                altimage=prize.altimage,
                imagefile=prize.imagefile.url if prize.imagefile else '',
                description=prize.description,
                shortdescription=prize.shortdescription,
                creator=prize.creator,
                creatoremail=prize.creatoremail,
                creatorwebsite=prize.creatorwebsite,
                key_code=prize.key_code,
                provider=prize.provider,
                maxmultiwin=prize.maxmultiwin,
                maxwinners=prize.maxwinners,
                numwinners=len(prize.get_prize_winners()),
                custom_country_filter=prize.custom_country_filter,
                estimatedvalue=prize.estimatedvalue,
                minimumbid=prize.minimumbid,
                maximumbid=prize.maximumbid,
                sumdonations=prize.sumdonations,
                randomdraw=prize.randomdraw,
                event=prize.event_id,
                startrun=prize.startrun_id,
                endrun=prize.endrun_id,
                starttime=prize.starttime,
                endtime=prize.endtime,
                tags=(t.id for t in prize.tags.all()),
                **run_fields,
                **draw_time_fields,
            ),
            model='tracker.prize',
            pk=prize.id,
        )

    format_model = format_prize

    def test_search(self):
        models.SpeedRun.objects.create(
            event=self.event,
            name='Test Run',
            run_time='5:00',
            setup_time='5:00',
            order=1,
        ).clean()
        prize = models.Prize.objects.create(
            event=self.event,
            handler=self.add_user,
            name='Prize With Image',
            state='ACCEPTED',
            startrun=self.event.speedrun_set.first(),
            endrun=self.event.speedrun_set.first(),
            image='https://example.com/example.jpg',
            maxwinners=3,
        )
        donors = randgen.generate_donors(self.rand, 3)
        models.PrizeWinner.objects.create(
            prize=prize, acceptcount=1, pendingcount=0, declinecount=0, winner=donors[0]
        )
        models.PrizeWinner.objects.create(
            prize=prize, acceptcount=0, pendingcount=1, declinecount=0, winner=donors[1]
        )
        models.PrizeWinner.objects.create(
            prize=prize, acceptcount=0, pendingcount=0, declinecount=1, winner=donors[2]
        )
        prize.refresh_from_db()
        request = self.factory.get(
            '/api/v1/search',
            dict(
                type='prize',
            ),
        )
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 1)
        self.assertModelPresent(self.format_prize(prize), data)

    def test_search_with_imagefile(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        models.SpeedRun.objects.create(
            event=self.event,
            name='Test Run',
            run_time='5:00',
            setup_time='5:00',
            order=1,
        ).clean()
        prize = models.Prize.objects.create(
            event=self.event,
            handler=self.add_user,
            name='Prize With Image',
            state='ACCEPTED',
            startrun=self.event.speedrun_set.first(),
            endrun=self.event.speedrun_set.first(),
            imagefile=SimpleUploadedFile('test.jpg', b''),
        )
        prize.refresh_from_db()
        request = self.factory.get(
            '/api/v1/search',
            dict(
                type='prize',
            ),
        )
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 1)
        self.assertModelPresent(prize, data)


class TestEvent(APITestCase):
    model_name = 'event'

    def setUp(self):
        super(TestEvent, self).setUp()

    def format_event(self, event):
        return dict(
            fields=dict(
                allow_donations=event.allow_donations,
                allowed_prize_countries=[],  # FIXME: natural keys?
                amount=0,  # FIXME: donation total
                avg=0,  # FIXME: donation average
                canonical_url=(
                    'http://testserver' + reverse('tracker:index', args=(event.id,))
                ),
                count=0,  # FIXME: donation count
                datetime=format_time(event.datetime),
                disallowed_prize_regions=[],  # FIXME: natural keys?
                hashtag=event.hashtag,
                locked=event.locked,
                max=0,  # FIXME: donation maximum
                minimumdonation=event.minimumdonation,
                name=event.name,
                paypalcurrency=event.paypalcurrency,
                paypalemail=event.paypalemail,
                public=str(event),
                receiver_short=event.receiver_short,
                receivername=event.receivername,
                short=event.short,
                timezone=str(event.timezone),
                use_one_step_screening=event.use_one_step_screening,
            ),
            model='tracker.event',
            pk=event.id,
        )

    def test_get_single(self):
        request = self.factory.get(
            '/api/v1/search', dict(type='event', id=self.event.id)
        )
        request.user = self.user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 1)
        expected = self.format_event(self.event)
        self.assertEqual(data[0], expected)

    def test_event_annotations(self):
        models.Donation.objects.create(
            event=self.event,
            amount=10,
            domain='PAYPAL',
            transactionstate='PENDING',
        )
        models.Donation.objects.create(event=self.event, amount=5, domainId='123457')
        # there was a bug where events with only pending donations wouldn't come back in the search
        models.Donation.objects.create(
            event=self.locked_event,
            amount=10,
            domain='PAYPAL',
            transactionstate='PENDING',
        )
        request = self.factory.get('/api/v1/search', dict(type='event'))
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 3)
        self.assertModelPresent(
            {
                'pk': self.event.id,
                'model': 'tracker.event',
                'fields': {'amount': 5.0, 'count': 1, 'max': 5.0, 'avg': 5.0},
            },
            data,
            partial=True,
        )
        self.assertModelPresent(
            {
                'pk': self.locked_event.id,
                'model': 'tracker.event',
                'fields': {'amount': 0.0, 'count': 0, 'max': 0.0, 'avg': 0.0},
            },
            data,
            partial=True,
        )
        self.assertModelPresent(
            {
                'pk': self.blank_event.id,
                'model': 'tracker.event',
                'fields': {'amount': 0.0, 'count': 0, 'max': 0.0, 'avg': 0.0},
            },
            data,
            partial=True,
        )


class TestBid(APITestCase):
    model_name = 'bid'

    @classmethod
    def format_bid(cls, bid, request):
        def add_run_fields(fields, run, prefix):
            dumped_run = TrackerSerializer(models.SpeedRun, request).serialize([run])[0]
            for key, value in dumped_run['fields'].items():
                if key not in [
                    'canonical_url',
                    'endtime',
                    'name',
                    'starttime',
                    'display_name',
                    'twitch_name',
                    'order',
                ]:
                    continue
                try:
                    value = DjangoJSONEncoder().default(value)
                except TypeError:
                    pass
                fields[prefix + '__' + key] = value
            fields[prefix + '__public'] = str(run)

        def add_parent_fields(fields, parent, prefix):
            dumped_bid = TrackerSerializer(models.Bid, request).serialize([parent])[0]
            for key, value in dumped_bid['fields'].items():
                if key not in [
                    'canonical_url',
                    'name',
                    'state',
                    'goal',
                    'allowuseroptions',
                    'option_max_length',
                    'count',
                ]:
                    continue
                try:
                    value = DjangoJSONEncoder().default(value)
                except TypeError:
                    pass
                fields[prefix + '__' + key] = value
            fields[prefix + '__total'] = Decimal(dumped_bid['fields']['total'])
            fields[prefix + '__public'] = str(parent)
            if parent.speedrun:
                add_run_fields(fields, parent.speedrun, prefix + '__speedrun')
            add_event_fields(fields, parent.event, prefix + '__event')

        def add_event_fields(fields, event, prefix):
            dumped_event = TrackerSerializer(models.Event, request).serialize([event])[
                0
            ]
            for key, value in dumped_event['fields'].items():
                if key not in ['canonical_url', 'name', 'short', 'timezone']:
                    continue
                try:
                    value = DjangoJSONEncoder().default(value)
                except TypeError:
                    pass
                fields[prefix + '__' + key] = value
            fields[prefix + '__datetime'] = event.datetime
            fields[prefix + '__public'] = str(event)

        run_fields = {}
        if bid.speedrun:
            add_run_fields(run_fields, bid.speedrun, 'speedrun')
        parent_fields = {}
        if bid.parent:
            add_parent_fields(parent_fields, bid.parent, 'parent')
        event_fields = {}
        add_event_fields(event_fields, bid.event, 'event')

        return dict(
            fields=dict(
                public=str(bid),
                name=bid.name,
                canonical_url=(reverse('tracker:bid', args=(bid.id,))),
                description=bid.description,
                shortdescription=bid.shortdescription,
                event=bid.event_id,
                speedrun=bid.speedrun_id,
                total=Decimal(bid.total),
                count=bid.count,
                goal=bid.goal,
                repeat=bid.repeat,
                state=bid.state,
                istarget=bid.istarget,
                pinned=bid.pinned,
                revealedtime=format_time(bid.revealedtime),
                allowuseroptions=bid.allowuseroptions,
                biddependency=bid.biddependency_id,
                option_max_length=bid.option_max_length,
                parent=bid.parent_id,
                **run_fields,
                **parent_fields,
                **event_fields,
            ),
            model='tracker.bid',
            pk=bid.id,
        )

    def test_bid_with_parent(self):
        models.SpeedRun.objects.create(
            event=self.event,
            name='Test Run',
            run_time='5:00',
            setup_time='5:00',
            order=1,
        ).clean()
        parent = models.Bid.objects.create(
            name='Parent',
            allowuseroptions=True,
            speedrun=self.event.speedrun_set.first(),
            state='OPENED',
        )
        parent.clean()
        parent.save()
        child = models.Bid.objects.create(
            name='Child',
            allowuseroptions=False,
            parent=parent,
        )
        child.clean()
        child.save()
        request = self.factory.get(
            '/api/v1/search', dict(type='allbids', event=self.event.id)
        )
        request.user = self.anonymous_user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 2)
        self.assertModelPresent(self.format_bid(parent, request), data)
        self.assertModelPresent(self.format_bid(child, request), data)


class TestDonation(APITestCase):
    model_name = 'donation'

    def setUp(self):
        super(TestDonation, self).setUp()
        self.add_user.user_permissions.add(
            Permission.objects.get(name='Can view all comments')
        )
        self.donor = randgen.generate_donor(self.rand, visibility='ANON')
        self.donor.save()

    @classmethod
    def format_donation(cls, donation, request):
        other_fields = {}

        # donor = donation.donor
        #
        # if donor.visibility in ['FULL', 'FIRST', 'ALIAS']:
        #     other_fields['donor__alias'] = donor.alias
        #     other_fields['donor__alias_num'] = donor.alias_num
        #     other_fields['donor__canonical_url'] = request.build_absolute_uri(
        #         donor.get_absolute_url()
        #     )
        #     other_fields['donor__visibility'] = donor.visibility
        #     other_fields['donor'] = donor.pk

        # FIXME: this is super weird but maybe not worth fixing
        # if 'all_comments' in request.GET:
        #     other_fields['donor__alias'] = donor.alias
        #     other_fields['donor__alias_num'] = donor.alias_num
        #     other_fields['donor__canonical_url'] = request.build_absolute_uri(
        #         donor.get_absolute_url()
        #     )
        #     other_fields['donor__visibility'] = donor.visibility
        #     other_fields['donor'] = donor.pk

        if donation.commentstate == 'APPROVED' or 'all_comments' in request.GET:
            other_fields['comment'] = donation.comment
            other_fields['commentlanguage'] = donation.commentlanguage

        return dict(
            fields=dict(
                amount=float(donation.amount),
                canonical_url=request.build_absolute_uri(donation.get_absolute_url()),
                commentstate=donation.commentstate,
                currency=donation.currency,
                domain=donation.domain,
                visible_donor_name=donation.visible_donor_name,
                # donor__public=donor.visible_name(),
                event=donation.event.pk,
                public=str(donation),
                readstate=donation.readstate,
                timereceived=format_time(donation.timereceived),
                transactionstate=donation.transactionstate,
                pinned=donation.pinned,
                **other_fields,
            ),
            model='tracker.donation',
            pk=donation.id,
        )

    def test_unapproved_comment(self):
        donation = randgen.generate_donation(
            self.rand, donor=self.donor, event=self.event, commentstate='PENDING'
        )
        donation.save()
        request = self.factory.get(
            reverse('tracker:api_v1:search'), dict(type='donation')
        )
        request.user = self.anonymous_user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 1)
        self.assertModelPresent(self.format_donation(donation, request), data)

    def test_unapproved_comment_with_permission(self):
        donation = randgen.generate_donation(
            self.rand, donor=self.donor, event=self.event, commentstate='PENDING'
        )
        donation.save()
        request = self.factory.get(
            reverse('tracker:api_v1:search'), dict(type='donation', all_comments='')
        )
        request.user = self.add_user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 1)
        self.assertModelPresent(self.format_donation(donation, request), data)

    def test_unapproved_comment_without_permission(self):
        request = self.factory.get(
            reverse('tracker:api_v1:search'), dict(type='donation', all_comments='')
        )
        request.user = self.anonymous_user
        self.parseJSON(tracker.views.api.search(request), status_code=403)

    def test_approved_comment(self):
        donation = randgen.generate_donation(
            self.rand, donor=self.donor, event=self.event
        )
        donation.save()
        request = self.factory.get(
            reverse('tracker:api_v1:search'), dict(type='donation')
        )
        request.user = self.anonymous_user
        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 1)
        self.assertModelPresent(self.format_donation(donation, request), data)

    def test_donor_visibilities(self):
        donation = randgen.generate_donation(
            self.rand, donor=self.donor, event=self.event
        )
        donation.save()
        for visibility in ['FULL', 'FIRST', 'ALIAS', 'ANON']:
            self.donor.visibility = visibility
            self.donor.save()
            donation.donor.refresh_from_db()
            request = self.factory.get(
                reverse('tracker:api_v1:search'), dict(type='donation')
            )
            request.user = self.anonymous_user
            data = self.parseJSON(tracker.views.api.search(request))
            self.assertEqual(len(data), 1)
            self.assertModelPresent(
                self.format_donation(donation, request),
                data,
                msg=f'Visibility {visibility} gave an incorrect result',
            )


class TestMilestone(APITestCase):
    model_name = 'milestone'

    @classmethod
    def format_milestone(cls, milestone, request):
        return dict(
            fields=dict(
                event=milestone.event_id,
                start=float(milestone.start),
                amount=float(milestone.amount),
                name=milestone.name,
                description=milestone.description,
                short_description=milestone.short_description,
                public=str(milestone),
                run=milestone.run_id,
                visible=milestone.visible,
            ),
            model='tracker.milestone',
            pk=milestone.pk,
        )

    def test_search(self):
        self.milestone = randgen.generate_milestone(self.rand, self.event)
        self.milestone.visible = True
        self.milestone.save()
        self.invisible_milestone = randgen.generate_milestone(self.rand, self.event)
        self.invisible_milestone.save()
        request = self.factory.get(
            reverse('tracker:api_v1:search'),
            dict(type='milestone', event=self.event.id),
        )
        request.user = self.anonymous_user

        data = self.parseJSON(tracker.views.api.search(request))
        self.assertEqual(len(data), 1)
        self.assertModelPresent(
            self.format_milestone(self.milestone, request),
            data,
            msg='Milestone search gave an incorrect result',
        )
