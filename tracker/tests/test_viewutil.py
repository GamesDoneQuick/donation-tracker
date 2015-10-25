import tracker.models as models
from tracker.views import parse_value

from django.test import TestCase, TransactionTestCase

import datetime


class TestUtil(TransactionTestCase):

    def test_parse_value(self):
        runner = parse_value('runner', '["UraniumAnchor"]')
        self.assertTrue(runner.id)
        self.assertEqual(runner.name, 'UraniumAnchor')

        event = models.Event.objects.create(
            date=datetime.date.today(), targetamount=5, short='agdq2015')
        self.assertEqual(parse_value('event', '["agdq2015"]'), event)
        run = parse_value('run', '["Mega Man 3", ["agdq2015"]]')
        self.assertTrue(run.id)
        self.assertEqual(run.name, 'Mega Man 3')
        self.assertEqual(run.event, event)

        self.assertEqual(parse_value('FAKE_FIELD', 'FAKE_VALUE'), 'FAKE_VALUE')
