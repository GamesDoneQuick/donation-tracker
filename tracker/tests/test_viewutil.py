import datetime

import tracker.models
import tracker.views
from django.test import TransactionTestCase

class TestUtil(TransactionTestCase):

    def test_parse_value(self):
        runner = tracker.views.api.parse_value('runner', '["UraniumAnchor"]')
        self.assertTrue(runner.id)
        self.assertEqual(runner.name, 'UraniumAnchor')

        event = tracker.models.Event.objects.create(
            date=datetime.date.today(), targetamount=5, short='agdq2015')
        self.assertEqual(tracker.views.api.parse_value('event', '["agdq2015"]'), event)
        run = tracker.views.api.parse_value('run', '["Mega Man 3", ["agdq2015"]]')
        self.assertTrue(run.id)
        self.assertEqual(run.name, 'Mega Man 3')
        self.assertEqual(run.event, event)

        self.assertEqual(tracker.views.api.parse_value('FAKE_FIELD', 'FAKE_VALUE'), 'FAKE_VALUE')
