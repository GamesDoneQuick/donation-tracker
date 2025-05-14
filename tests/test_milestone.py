import random

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from tracker.models import Milestone

from . import randgen
from .util import APITestCase, MigrationsTestCase, today_noon, tomorrow_noon


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
        self.draft_event = randgen.generate_event(self.rand, tomorrow_noon)
        self.draft_event.draft = True
        self.draft_event.save()
        self.visible_milestone = randgen.generate_milestone(self.rand, self.event)
        self.visible_milestone.visible = True
        self.visible_milestone.save()
        self.invisible_milestone = randgen.generate_milestone(self.rand, self.event)
        self.invisible_milestone.save()
        self.draft_milestone = randgen.generate_milestone(self.rand, self.draft_event)
        self.draft_milestone.save()

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
        self.assertNotContains(
            resp, reverse('tracker:milestoneindex', args=(self.draft_event.short,))
        )

    def test_milestone_list(self):
        resp = self.client.get(
            reverse('tracker:milestoneindex', args=(self.event.short,))
        )
        self.assertContains(resp, self.visible_milestone.name)
        self.assertNotContains(resp, self.invisible_milestone.name)

        resp = self.client.get(
            reverse('tracker:milestoneindex', args=(self.draft_event.short,))
        )
        self.assertEqual(resp.status_code, 404, msg='Draft event did not 404')


class TestMilestoneTargetMigration(MigrationsTestCase):
    migrate_from = (('tracker', '0052_delete_interview_text_columns'),)
    migrate_to = (('tracker', '0054_delete_event_targetamount'),)

    def setUpBeforeMigration(self, apps):
        Event = apps.get_model('tracker', 'Event')
        Event.objects.create(
            name='Test', short='test', targetamount=500, datetime=today_noon
        )
        Event.objects.create(
            name='Empty Test', short='empty', targetamount=0, datetime=tomorrow_noon
        )

    def test_milestone_created(self):
        Milestone = self.apps.get_model('tracker', 'Milestone')
        self.assertEqual(Milestone.objects.count(), 1)
        self.assertEqual(Milestone.objects.first().amount, 500)
