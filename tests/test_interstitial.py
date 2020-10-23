from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from tracker import models

from .util import today_noon, APITestCase


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
        self.assertSetEqual(
            set(models.Interstitial.interstitials_for_run(self.run1)), {i1, i2, i3}
        )
        self.assertSetEqual(
            set(models.Interstitial.interstitials_for_run(self.run3)), {i4}
        )
        self.assertSetEqual(
            set(models.Interstitial.interstitials_for_run(self.run4)), {i5, i6}
        )

    def test_move_interstitial_up_within_run(self):
        i1 = models.Interstitial.objects.create(
            event=self.event1, order=self.run2.order, suborder=1
        )
        i2 = models.Interstitial.objects.create(
            event=self.event1, order=self.run2.order, suborder=2
        )
        i3 = models.Interstitial.objects.create(
            event=self.event1, order=self.run2.order, suborder=3
        )
        self.client.force_login(self.superuser)
        resp = self.client.post(
            reverse('tracker:api_v1:interstitial'),
            {'id': i3.id, 'order': self.run2.order, 'suborder': i2.suborder,},
        )
        self.assertEqual(resp.status_code, 200)
        i1.refresh_from_db()
        i2.refresh_from_db()
        i3.refresh_from_db()
        self.assertEqual(i1.suborder, 1)
        self.assertEqual(i2.suborder, 3)
        self.assertEqual(i3.suborder, 2)

    def test_move_interstitial_down_within_run(self):
        i1 = models.Interstitial.objects.create(
            event=self.event1, order=self.run2.order, suborder=1
        )
        i2 = models.Interstitial.objects.create(
            event=self.event1, order=self.run2.order, suborder=2
        )
        i3 = models.Interstitial.objects.create(
            event=self.event1, order=self.run2.order, suborder=3
        )
        self.client.force_login(self.superuser)
        resp = self.client.post(
            reverse('tracker:api_v1:interstitial'),
            {'id': i1.id, 'order': self.run2.order, 'suborder': i2.suborder,},
        )
        self.assertEqual(resp.status_code, 200)
        i1.refresh_from_db()
        i2.refresh_from_db()
        i3.refresh_from_db()
        self.assertEqual(i1.suborder, 2)
        self.assertEqual(i2.suborder, 1)
        self.assertEqual(i3.suborder, 3)

    def test_move_interstitial_up_between_run(self):
        i1 = models.Interstitial.objects.create(
            event=self.event1, order=self.run2.order, suborder=1
        )
        i2 = models.Interstitial.objects.create(
            event=self.event1, order=self.run2.order, suborder=2
        )
        i3 = models.Interstitial.objects.create(
            event=self.event1, order=self.run2.order, suborder=3
        )
        i4 = models.Interstitial.objects.create(
            event=self.event1, order=self.run3.order, suborder=1
        )
        i5 = models.Interstitial.objects.create(
            event=self.event1, order=self.run3.order, suborder=2
        )
        i6 = models.Interstitial.objects.create(
            event=self.event1, order=self.run3.order, suborder=3
        )
        self.client.force_login(self.superuser)
        resp = self.client.post(
            reverse('tracker:api_v1:interstitial'),
            {'id': i2.id, 'order': self.run3.order, 'suborder': i6.suborder,},
        )
        self.assertEqual(resp.status_code, 200)
        i1.refresh_from_db()
        i2.refresh_from_db()
        i3.refresh_from_db()
        i4.refresh_from_db()
        i5.refresh_from_db()
        i6.refresh_from_db()
        self.assertEqual(i1.suborder, 1)
        self.assertEqual(i3.suborder, 2)
        self.assertEqual(i4.suborder, 1)
        self.assertEqual(i5.suborder, 2)
        self.assertEqual(i2.order, self.run3.order)
        self.assertEqual(i2.suborder, 3)
        self.assertEqual(i6.suborder, 4)

    def test_move_interstitial_down_between_run(self):
        i1 = models.Interstitial.objects.create(
            event=self.event1, order=self.run2.order, suborder=1
        )
        i2 = models.Interstitial.objects.create(
            event=self.event1, order=self.run2.order, suborder=2
        )
        i3 = models.Interstitial.objects.create(
            event=self.event1, order=self.run2.order, suborder=3
        )
        i4 = models.Interstitial.objects.create(
            event=self.event1, order=self.run3.order, suborder=1
        )
        i5 = models.Interstitial.objects.create(
            event=self.event1, order=self.run3.order, suborder=2
        )
        i6 = models.Interstitial.objects.create(
            event=self.event1, order=self.run3.order, suborder=3
        )
        self.client.force_login(self.superuser)
        resp = self.client.post(
            reverse('tracker:api_v1:interstitial'),
            {'id': i5.id, 'order': self.run2.order, 'suborder': i2.suborder,},
        )
        self.assertEqual(resp.status_code, 200)
        i1.refresh_from_db()
        i2.refresh_from_db()
        i3.refresh_from_db()
        i4.refresh_from_db()
        i5.refresh_from_db()
        i6.refresh_from_db()
        self.assertEqual(i1.suborder, 1)
        self.assertEqual(i5.order, self.run2.order)
        self.assertEqual(i5.suborder, 2)
        self.assertEqual(i2.suborder, 3)
        self.assertEqual(i3.suborder, 4)
        self.assertEqual(i4.suborder, 1)
        self.assertEqual(i6.suborder, 2)

    def test_move_interstitial_fill_holes(self):
        i1 = models.Interstitial.objects.create(
            event=self.event1, order=self.run2.order, suborder=1
        )
        i2 = models.Interstitial.objects.create(
            event=self.event1, order=self.run2.order, suborder=3
        )
        i3 = models.Interstitial.objects.create(
            event=self.event1, order=self.run2.order, suborder=5
        )
        i4 = models.Interstitial.objects.create(
            event=self.event1, order=self.run3.order, suborder=3
        )
        i5 = models.Interstitial.objects.create(
            event=self.event1, order=self.run3.order, suborder=7
        )
        self.client.force_login(self.superuser)
        resp = self.client.post(
            reverse('tracker:api_v1:interstitial'),
            {'id': i2.id, 'order': self.run3.order, 'suborder': -1,},
        )
        self.assertEqual(resp.status_code, 200)
        i1.refresh_from_db()
        i2.refresh_from_db()
        i3.refresh_from_db()
        i4.refresh_from_db()
        i5.refresh_from_db()
        self.assertEqual(i1.suborder, 1)
        self.assertEqual(i3.suborder, 2)
        self.assertEqual(i4.suborder, 1)
        self.assertEqual(i5.suborder, 2)
        self.assertEqual(i2.order, self.run3.order)
        self.assertEqual(i2.suborder, 3)


class TestAd(APITestCase):
    model_name = 'ad'

    @classmethod
    def format_ad(cls, ad):
        return dict(
            fields=dict(
                event_id=ad.event_id,
                length=ad.length,
                ad_type=ad.ad_type,
                filename=ad.filename,
                order=ad.order,
                suborder=ad.suborder,
                sponsor_name=ad.sponsor_name,
                ad_name=ad.ad_name,
            ),
            model='tracker.ad',
            pk=ad.id,
        )

    def test_ads_endpoint(self):
        models.SpeedRun.objects.create(event=self.event, name='Test Run 1', order=1)
        ad = models.Ad.objects.create(event=self.event, order=1, suborder=1)
        ad.refresh_from_db()
        resp = self.client.get(reverse('tracker:api_v1:ads', args=(self.event.id,)))
        self.assertEqual(resp.status_code, 403)
        self.client.force_login(self.view_user)
        resp = self.client.get(reverse('tracker:api_v1:ads', args=(self.event.id,)))
        data = self.parseJSON(resp)
        self.assertModelPresent(self.format_ad(ad), data)
