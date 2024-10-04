import json

from django.contrib.auth.models import User
from django.test import TransactionTestCase

from tracker import models
from tracker.views import parse_value

from .util import today_noon


class TestParseValue(TransactionTestCase):
    def setUp(self):
        super(TestParseValue, self).setUp()
        self.event = models.Event.objects.create(
            datetime=today_noon, targetamount=5, short='agdq2015'
        )
        self.super_user = User.objects.create(username='superuser', is_superuser=True)
        self.runner1 = models.Talent.objects.create(name='trihex')
        self.runner2 = models.Talent.objects.create(name='PJ')

    def test_single_pk_fetch(self):
        self.assertEqual(
            parse_value(models.SpeedRun, 'event', self.event.pk), self.event
        )

    def test_single_pk_as_string_fetch(self):
        self.assertEqual(
            parse_value(models.SpeedRun, 'event', str(self.event.pk)), self.event
        )

    def test_single_natural_key_as_string_fetch(self):
        self.assertEqual(
            parse_value(models.SpeedRun, 'event', self.event.short), self.event
        )

    def test_single_natural_key_as_json_fetch(self):
        self.assertEqual(
            parse_value(models.SpeedRun, 'event', json.dumps(self.event.natural_key())),
            self.event,
        )

    def test_single_natural_key_as_string_create(self):
        runner = parse_value(
            models.Submission, 'runner', 'UraniumAnchor', self.super_user
        )
        self.assertTrue(runner.id)
        self.assertEqual(runner.name, 'UraniumAnchor')

    def test_single_natural_key_as_json_create(self):
        runner = parse_value(
            models.Submission, 'runner', '["UraniumAnchor"]', self.super_user
        )
        self.assertTrue(runner.id)
        self.assertEqual(runner.name, 'UraniumAnchor')

    def test_complex_natural_key_as_json_create(self):
        run = parse_value(
            models.Bid,
            'speedrun',
            '["Mega Man 3", ["%s"]]' % self.event.short,
            self.super_user,
        )
        self.assertTrue(run.id)
        self.assertEqual(run.name, 'Mega Man 3')
        self.assertEqual(run.event, self.event)

    def test_m2m_pk_csv_fetch(self):
        expected_runners = [self.runner1, self.runner2]
        runners = parse_value(
            models.SpeedRun, 'runners', ','.join(str(r.pk) for r in expected_runners)
        )
        self.assertEqual(runners, expected_runners)

    def test_m2m_pk_csv_bad_fetch(self):
        with self.assertRaises(models.Talent.DoesNotExist):
            parse_value(models.SpeedRun, 'runners', '1001,1002')

    def test_m2m_pk_json_fetch(self):
        expected_runners = [self.runner1, self.runner2]
        runners = parse_value(
            models.SpeedRun, 'runners', json.dumps([r.pk for r in expected_runners])
        )
        self.assertEqual(runners, expected_runners)

    def test_m2m_pk_json_bad_fetch(self):
        with self.assertRaises(models.Talent.DoesNotExist):
            parse_value(models.SpeedRun, 'runners', '[1001,1002]')

    def test_m2m_natural_key_csv_fetch(self):
        expected_runners = [self.runner1, self.runner2]
        runners = parse_value(
            models.SpeedRun, 'runners', ','.join(r.name for r in expected_runners)
        )
        self.assertEqual(runners, expected_runners)

    def test_m2m_natural_key_csv_bad_fetch(self):
        with self.assertRaises(models.Talent.DoesNotExist):
            parse_value(models.SpeedRun, 'runners', 'total,nonsense')

    def test_m2m_natural_key_flat_json_fetch(self):
        expected_runners = [self.runner1, self.runner2]
        runners = parse_value(
            models.SpeedRun, 'runners', json.dumps([r.name for r in expected_runners])
        )
        self.assertEqual(runners, expected_runners)

    def test_m2m_natural_key_flat_json_bad_fetch(self):
        with self.assertRaises(models.Talent.DoesNotExist):
            parse_value(models.SpeedRun, 'runners', '["total","nonsense"]')

    def test_m2m_natural_key_full_json_fetch(self):
        expected_runners = [self.runner1, self.runner2]
        runners = parse_value(
            models.SpeedRun,
            'runners',
            json.dumps([r.natural_key() for r in expected_runners]),
        )
        self.assertEqual(runners, expected_runners)

    def test_m2m_natural_key_full_json_bad_fetch(self):
        with self.assertRaises(models.Talent.DoesNotExist):
            parse_value(models.SpeedRun, 'runners', '[["total"],["nonsense"]]')
