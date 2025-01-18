from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from tracker import models

from . import randgen
from .util import APITestCase, MigrationsTestCase, today_noon


class TestInterstitial(TestCase):
    def setUp(self):
        self.event1 = models.Event.objects.create(short='test1', datetime=today_noon)
        self.event2 = models.Event.objects.create(short='test2', datetime=today_noon)
        self.run1 = models.SpeedRun.objects.create(
            event=self.event1, name='Test Run 1', order=1
        )
        self.run2 = models.SpeedRun.objects.create(
            event=self.event1, name='Test Run 2', order=2
        )
        self.run3 = models.SpeedRun.objects.create(
            event=self.event1, name='Test Run 3', order=3
        )
        self.run4 = models.SpeedRun.objects.create(
            event=self.event1, name='Test Run 4', order=4
        )
        self.superuser = User.objects.create_superuser(
            'super', 'super@example.com', 'password'
        )

    def assertInterstitialOrder(self, interstitial_dict):
        for run, interstitials in interstitial_dict.items():
            actual = models.Interstitial.objects.for_run(run)
            for i in interstitials:
                i.refresh_from_db()
            with self.subTest(str(run)):
                # if provided a list, the order should match exactly, else it is an unordered set (because of holes in the schedule)
                if isinstance(interstitials, list):
                    self.assertEqual(
                        list(actual),
                        list(interstitials),
                        msg='Ordered list did not match',
                    )
                    for n, e in enumerate(interstitials, start=1):
                        e.refresh_from_db()
                        with self.subTest(f'interstitial #{n}'):
                            self.assertEqual(n, e.suborder, msg='Order was wrong')
                else:
                    self.assertEqual(
                        set(actual), set(interstitials), msg='Sets did not match'
                    )

    def test_closest_run_existing_run(self):
        interstitial = models.Interstitial.objects.create(
            event=self.event1, order=self.run2.order, suborder=1
        )
        self.assertEqual(interstitial.run, self.run2)

    def test_closest_run_previous(self):
        interstitial = models.Interstitial.objects.create(
            event=self.event1, order=self.run3.order, suborder=1
        )
        self.run3.delete()
        self.assertEqual(interstitial.run, self.run2)

    def test_closest_run_next(self):
        interstitial = models.Interstitial.objects.create(
            event=self.event1, order=self.run1.order, suborder=1
        )
        self.run1.delete()
        self.assertEqual(interstitial.run, self.run2)

    def test_closest_run_none(self):
        interstitial = models.Interstitial.objects.create(
            event=self.event1, order=self.run2.order, suborder=1
        )
        self.run1.delete()
        self.run2.delete()
        self.run3.delete()
        self.run4.delete()
        self.assertEqual(interstitial.run, None)

    def test_interstitials_for_run(self):
        self.run2.delete()
        i1 = models.Interstitial.objects.create(
            event=self.event1, order=self.run1.order - 1, suborder=1
        )
        i2 = models.Interstitial.objects.create(
            event=self.event1, order=self.run1.order, suborder=2
        )
        i3 = models.Interstitial.objects.create(
            event=self.event1, order=self.run1.order + 1, suborder=1
        )
        i4 = models.Interstitial.objects.create(
            event=self.event1, order=self.run3.order, suborder=1
        )
        i5 = models.Interstitial.objects.create(
            event=self.event1, order=self.run4.order, suborder=2
        )
        i6 = models.Interstitial.objects.create(
            event=self.event1, order=self.run4.order + 1, suborder=1
        )
        self.assertInterstitialOrder(
            {
                self.run1: {i1, i2, i3},
                self.run3: [i4],
                self.run4: {i5, i6},
            }
        )

    # smoke test
    def test_full_schedule(self):
        ad = models.Ad.objects.create(
            event=self.event1, order=self.run1.order, suborder=1, sponsor_name='Yetee'
        )
        interview = models.Interview.objects.create(
            event=self.event1, order=self.run4.order, suborder=1
        )
        interview.interviewers.add(models.Talent.objects.create(name='feasel'))
        self.client.force_login(self.superuser)
        resp = self.client.get(
            reverse('admin:view_full_schedule', args=(self.event1.pk,))
        )
        self.assertContains(
            resp, reverse('admin:tracker_speedrun_change', args=(self.run1.id,))
        )
        self.assertContains(resp, reverse('admin:tracker_ad_change', args=(ad.id,)))
        self.assertContains(resp, ad.sponsor_name)
        self.assertContains(
            resp, reverse('admin:tracker_interview_change', args=(interview.id,))
        )
        self.assertContains(resp, 'feasel')


class TestInterview(APITestCase):
    model_name = 'interview'

    def setUp(self):
        super().setUp()
        self.run = randgen.generate_run(self.rand, event=self.event, ordered=True)
        self.run.save()
        self.public_interview = randgen.generate_interview(self.rand, run=self.run)
        self.public_interview.save()
        self.private_interview = randgen.generate_interview(self.rand, run=self.run)
        self.private_interview.public = False
        self.private_interview.save()

    def test_for_run(self):
        self.ad = models.Ad.objects.create(
            event=self.event,
            order=self.run.order,
            suborder=self.private_interview.suborder + 1,
        )
        self.assertQuerySetEqual(
            models.Interview.objects.for_run(self.run),
            [self.public_interview, self.private_interview],
        )


class TestAd(APITestCase):
    model_name = 'ad'

    def setUp(self):
        super().setUp()
        self.run = randgen.generate_run(self.rand, event=self.event, ordered=True)
        self.run.save()
        # TODO: randgen.generate_ad
        self.ad = models.Ad.objects.create(event=self.event, order=1, suborder=1)

    def test_for_run(self):
        randgen.generate_interview(self.rand, run=self.run).save()
        self.assertQuerySetEqual(models.Ad.objects.for_run(self.run), [self.ad])


class TestInterviewTalentMigration(MigrationsTestCase):
    migrate_from = (('tracker', '0049_add_milestone_run'),)
    migrate_to = (('tracker', '0052_delete_interview_text_columns'),)

    def setUpBeforeMigration(self, apps):
        Event = apps.get_model('tracker', 'Event')
        Interview = apps.get_model('tracker', 'Interview')
        Talent = apps.get_model('tracker', 'Talent')
        Talent.objects.create(name='Existing Interviewer')
        Talent.objects.create(name='Existing Subject')

        Interview.objects.create(
            event=Event.objects.create(name='Test', short='test', datetime=today_noon),
            order=1,
            suborder=1,
            interviewers='Existing Interviewer, New Interviewer, ,',  # test blank entry
            subjects='Existing Subject, New Subject, Three Kobolds in a Trenchcoat and their Amazing Friends',
            topic='Test Interview',
        )

    def test_migration(self):
        Interview = self.apps.get_model('tracker', 'Interview')
        Talent = self.apps.get_model('tracker', 'Talent')
        expected_talent = Talent.objects.filter(
            name__in=[
                'Existing Interviewer',
                'Existing Subject',
                'New Interviewer',
                'New Subject',
                'Three Kobolds in a Trenchcoat and their Amazing Friends',
            ]
        )
        self.assertEqual(len(expected_talent), 5, msg='Some Talent was missing')
        self.assertFalse(
            Talent.objects.filter(name='').exists(), msg='Blank Talent was created'
        )
        interview = Interview.objects.prefetch_related('interviewers', 'subjects').get(
            topic='Test Interview'
        )
        self.assertSetEqual(
            {'Existing Interviewer', 'New Interviewer'},
            set(t.name for t in interview.interviewers.all()),
        )
        self.assertSetEqual(
            {
                'Existing Subject',
                'New Subject',
                'Three Kobolds in a Trenchcoat and their Amazing Friends',
            },
            set(t.name for t in interview.subjects.all()),
        )
