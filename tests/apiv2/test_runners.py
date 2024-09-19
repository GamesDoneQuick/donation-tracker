import random

from tests import randgen
from tests.util import APITestCase
from tracker.api.serializers import RunnerSerializer


class TestRunners(APITestCase):
    model_name = 'runner'
    serializer_class = RunnerSerializer

    def setUp(self):
        super().setUp()
        self.rand = random.Random()
        self.event = randgen.generate_event(self.rand)
        self.event.save()
        self.runner = randgen.generate_runner(self.rand)
        self.runner.save()
        self.other_runner = randgen.generate_runner(self.rand)
        self.other_runner.save()
        self.runs = randgen.generate_runs(
            self.rand, num_runs=2, event=self.event, ordered=True
        )
        self.runner.speedrun_set.add(*self.runs)

    def test_runner_fetch(self):
        data = self.get_list()['results']
        self.assertEqual(len(data), 2)
        self.assertV2ModelPresent(self.runner, data)
        self.assertV2ModelPresent(self.other_runner, data)

        data = self.get_list(kwargs={'event_pk': self.event.pk})['results']
        self.assertEqual(len(data), 1)
        self.assertV2ModelPresent(self.runner, data)
        self.assertV2ModelNotPresent(self.other_runner, data)
