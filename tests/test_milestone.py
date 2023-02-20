import random

from django.test import TestCase
from django.urls import reverse

from . import randgen
from .util import today_noon


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
