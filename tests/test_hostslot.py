from django.core.exceptions import ValidationError
from django.test import TestCase
from tracker import models

from .util import today_noon


class TestHostSlot(TestCase):
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
        self.run5 = models.SpeedRun.objects.create(
            event=self.event1, name='Test Run 5', order=5
        )
        self.run_unordered = models.SpeedRun.objects.create(
            event=self.event1, name='Test Run 0', order=None
        )
        self.run_other = models.SpeedRun.objects.create(
            event=self.event2, name='Test Run Other 1', order=1
        )

    def test_normal(self):
        models.HostSlot.objects.create(
            start_run=self.run1, end_run=self.run2, name='Prolix'
        )
        models.HostSlot(start_run=self.run3, end_run=self.run3, name='Prolix').clean()

    def test_overlapping(self):
        created = models.HostSlot.objects.create(
            start_run=self.run2, end_run=self.run4, name='Prolix'
        )
        created.clean()
        with self.assertRaises(ValidationError):
            models.HostSlot(
                start_run=self.run1, end_run=self.run2, name='Prolix'
            ).clean()
        with self.assertRaises(ValidationError):
            models.HostSlot(
                start_run=self.run3, end_run=self.run3, name='Prolix'
            ).clean()
        with self.assertRaises(ValidationError):
            models.HostSlot(
                start_run=self.run4, end_run=self.run5, name='Prolix'
            ).clean()
        with self.assertRaises(ValidationError):
            models.HostSlot(
                start_run=self.run1, end_run=self.run5, name='Prolix'
            ).clean()

    def test_overlapping_different_events(self):
        created = models.HostSlot.objects.create(
            start_run=self.run1, end_run=self.run1, name='Prolix'
        )
        created.clean()
        created_other = models.HostSlot.objects.create(
            start_run=self.run_other, end_run=self.run_other, name='Prolix'
        )
        created_other.clean()

    def test_different_events(self):
        with self.assertRaises(ValidationError):
            models.HostSlot(
                start_run=self.run1, end_run=self.run_other, name='Prolix'
            ).clean()

    def test_wrong_order(self):
        with self.assertRaises(ValidationError):
            models.HostSlot(
                start_run=self.run2, end_run=self.run1, name='Prolix'
            ).clean()

    def test_no_order(self):
        with self.assertRaises(ValidationError):
            models.HostSlot(
                start_run=self.run_unordered, end_run=self.run1, name='Prolix'
            ).clean()
        with self.assertRaises(ValidationError):
            models.HostSlot(
                start_run=self.run1, end_run=self.run_unordered, name='Prolix'
            ).clean()

    def test_host_for_run(self):
        slot = models.HostSlot.objects.create(
            start_run=self.run2, end_run=self.run4, name='Prolix'
        )
        slot2 = models.HostSlot.objects.create(
            start_run=self.run_other, end_run=self.run_other, name='Prolix'
        )
        self.assertEqual(models.HostSlot.host_for_run(self.run1), None)
        with self.assertNumQueries(0):  # caching behavior
            self.assertEqual(models.HostSlot.host_for_run(self.run2), slot)
            self.assertEqual(models.HostSlot.host_for_run(self.run3), slot)
            self.assertEqual(models.HostSlot.host_for_run(self.run4), slot)
            self.assertEqual(models.HostSlot.host_for_run(self.run5), None)
        self.assertEqual(models.HostSlot.host_for_run(self.run_other), slot2)
