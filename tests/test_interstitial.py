from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from tracker import models

from . import randgen
from .util import APITestCase, today_noon


class TestInterstitial(TestCase):
    def setUp(self):
        self.event1 = models.Event.objects.create(
            short='test1', datetime=today_noon, targetamount=5
        )
        self.event2 = models.Event.objects.create(
            short='test2', datetime=today_noon, targetamount=5
        )
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
            event=self.event1, order=self.run4.order, suborder=1, interviewers='feasel'
        )
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
        self.assertContains(resp, interview.interviewers)


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

    @classmethod
    def format_interview(cls, interview):
        return dict(
            fields=dict(
                event_id=interview.event_id,
                order=interview.order,
                suborder=interview.suborder,
                social_media=interview.social_media,
                interviewers=interview.interviewers,
                topic=interview.topic,
                public=interview.public,
                prerecorded=interview.prerecorded,
                producer=interview.producer,
                clips=interview.clips,
                length=interview.length,
                subjects=interview.subjects,
                camera_operator=interview.camera_operator,
                anchor=interview.anchor_id,
                tags=[t.id for t in interview.tags.all()],
            ),
            model='tracker.interview',
            pk=interview.id,
        )

    format_model = format_interview

    def test_public_fetch(self):
        resp = self.client.get(
            reverse('tracker:api_v1:interviews', args=(self.event.id,))
        )
        data = self.parseJSON(resp)
        self.assertModelPresent(self.public_interview, data)
        self.assertModelNotPresent(self.private_interview, data)

    def test_private_fetch(self):
        resp = self.client.get(
            reverse('tracker:api_v1:interviews', args=(self.event.id,)),
            data={'all': ''},
        )
        self.parseJSON(resp, status_code=403)
        self.client.force_login(self.view_user)
        resp = self.client.get(
            reverse('tracker:api_v1:interviews', args=(self.event.id,)),
            data={'all': ''},
        )
        data = self.parseJSON(resp)
        self.assertModelPresent(self.public_interview, data)
        self.assertModelPresent(self.private_interview, data)

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

    @classmethod
    def format_ad(cls, ad):
        return dict(
            fields=dict(
                event_id=ad.event_id,
                length=ad.length,
                ad_type=ad.ad_type,
                filename=ad.filename,
                anchor=ad.anchor_id,
                order=ad.order,
                suborder=ad.suborder,
                sponsor_name=ad.sponsor_name,
                ad_name=ad.ad_name,
                blurb=ad.blurb,
                tags=(t.id for t in ad.tags.all()),
            ),
            model='tracker.ad',
            pk=ad.id,
        )

    format_model = format_ad

    def test_ads_endpoint(self):
        resp = self.client.get(reverse('tracker:api_v1:ads', args=(self.event.id,)))
        self.assertEqual(resp.status_code, 403)
        self.client.force_login(self.view_user)
        resp = self.client.get(reverse('tracker:api_v1:ads', args=(self.event.id,)))
        data = self.parseJSON(resp)
        self.assertModelPresent(self.ad, data)

    def test_for_run(self):
        randgen.generate_interview(self.rand, run=self.run).save()
        self.assertQuerySetEqual(models.Ad.objects.for_run(self.run), [self.ad])
