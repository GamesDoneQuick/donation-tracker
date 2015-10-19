import tracker.models as models
import tracker.viewutil as viewutil
import tracker.randgen as randgen

from django.test import TestCase, TransactionTestCase

from dateutil.parser import parse as parse_date
import random


class TestMergeSchedule(TransactionTestCase):

    def setUp(self):
        self.eventStart = parse_date("2012-01-01 01:00:00")
        self.rand = random.Random(632434)
        self.event = randgen.build_random_event(
            self.rand, startTime=self.eventStart)
        self.event.scheduledatetimefield = "time"
        self.event.schedulegamefield = "game"
        self.event.schedulerunnersfield = "runners"
        self.event.scheduleestimatefield = "estimate"
        self.event.schedulesetupfield = "setup"
        self.event.schedulecommentatorsfield = "commentators"
        self.event.schedulecommentsfield = "comments"
        self.event.save()

    def test_case_sensitive_runs(self):
        ssRuns = []
        ssRuns.append({"time": "9/5/2014 12:00:00", "game": "CaSe SeNsItIvE", "runners": "A Runner1",
                       "estimate": "1:00:00", "setup": "0:00:00", "commentators": "", "comments": ""})
        viewutil.merge_schedule_list(self.event, ssRuns)
        runs = models.SpeedRun.objects.filter(event=self.event)
        self.assertEqual(1, runs.count())
        self.assertEqual("CaSe SeNsItIvE", runs[0].name)

    def test_delete_missing_runs(self):
        ssRuns = []
        ssRuns.append({"time": "9/5/2014 12:00:00", "game": "Game 1", "runners": "A Runner1",
                       "estimate": "1:00:00", "setup": "0:00:00", "commentators": "", "comments": ""})
        ssRuns.append({"time": "9/5/2014 13:00:00", "game": "Game 2", "runners": "A Runner2",
                       "estimate": "1:30:00", "setup": "0:00:00", "commentators": "", "comments": ""})
        ssRuns.append({"time": "9/5/2014 14:30:00", "game": "Game 3", "runners": "A Runner3",
                       "estimate": "2:00:00", "setup": "0:00:00", "commentators": "", "comments": ""})
        viewutil.merge_schedule_list(self.event, ssRuns)
        runs = models.SpeedRun.objects.filter(event=self.event)
        self.assertEqual(3, runs.count())
        ssRuns.pop(1)
        viewutil.merge_schedule_list(self.event, ssRuns)
        runs = models.SpeedRun.objects.filter(event=self.event)
        self.assertEqual(2, runs.count())
        self.assertEqual("Game 1", runs[0].name)
        self.assertEqual("Game 3", runs[1].name)
