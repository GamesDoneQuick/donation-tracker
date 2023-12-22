import random

from tests import randgen
from tests.util import APITestCase
from tracker.api.serializers import InterviewSerializer


class TestInterviews(APITestCase):
    model_name = 'interview'
    serializer_class = InterviewSerializer
    rand = random.Random()

    def setUp(self):
        super().setUp()
        self.run = randgen.generate_run(self.rand, event=self.event, ordered=True)
        self.run.save()
        self.public_interview = randgen.generate_interview(self.rand, run=self.run)
        self.public_interview.save()
        self.private_interview = randgen.generate_interview(self.rand, run=self.run)
        self.private_interview.public = False
        self.private_interview.save()

    def test_public_fetch(self):
        data = self.get_detail(self.public_interview)
        self.assertV2ModelPresent(self.public_interview, data)

    def test_private_fetch(self):
        self.get_detail(self.private_interview, status_code=404)

        self.client.force_authenticate(self.view_user)

        data = self.get_detail(self.private_interview)
        self.assertV2ModelPresent(self.private_interview, data)

    def test_public_list(self):
        data = self.get_list()['results']
        self.assertV2ModelPresent(self.public_interview, data)
        self.assertV2ModelNotPresent(self.private_interview, data)

    def test_private_list(self):
        self.get_list(data={'all': ''}, status_code=403)

        self.client.force_authenticate(self.view_user)
        data = self.get_list(data={'all': ''})['results']
        self.assertV2ModelPresent(self.public_interview, data)
        self.assertV2ModelPresent(self.private_interview, data)
