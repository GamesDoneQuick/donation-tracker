import random

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from tracker.models import Milestone

from . import randgen
from .util import APITestCase, today_noon


class TestMilestone(APITestCase):
    model_name = 'milestone'

    def setUp(self):
        super().setUp()
        self.milestone = Milestone.objects.create(
            event=self.event, name='Test Milestone', amount=1000
        )

    def test_validation(self):
        with self.assertRaises(ValidationError):
            self.milestone.start = 1000
            self.milestone.clean()

        self.milestone.start = 500
        self.milestone.clean()

        self.milestone.start = 0
        self.milestone.clean()

        with self.assertRaises(ValidationError):
            self.milestone.start = -1
            self.milestone.full_clean()


class TestMilestoneViews(TestCase):
    def setUp(self):
        super(TestMilestoneViews, self).setUp()
        self.rand = random.Random()
        self.event = randgen.generate_event(self.rand, today_noon)
        self.event.save()
        self.visible_milestone = randgen.generate_milestone(self.rand, self.event)
        self.visible_milestone.visible = True
        self.visible_milestone.save()
        self.invisible_milestone = randgen.generate_milestone(self.rand, self.event)
        self.invisible_milestone.save()

    def test_milestone_index(self):
        resp = self.client.get(
            reverse(
                'tracker:milestoneindex',
            )
        )
        self.assertContains(resp, self.event.name)
        self.assertContains(
            resp, reverse('tracker:milestoneindex', args=(self.event.short,))
        )

    def test_milestone_list(self):
        resp = self.client.get(
            reverse('tracker:milestoneindex', args=(self.event.short,))
        )
        self.assertContains(resp, self.visible_milestone.name)
        self.assertNotContains(resp, self.invisible_milestone.name)
