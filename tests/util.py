import datetime
import itertools
import json
import random

import pytz
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User, Permission
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, RequestFactory

import models


def parse_test_mail(mail):
    lines = list(
        [
            x.partition(':')
            for x in [x for x in [x.strip() for x in mail.message.split('\n')] if x]
        ]
    )
    result = {}
    for line in lines:
        if line[2]:
            name = line[0].lower()
            value = line[2]
            if name not in result:
                result[name] = []
            result[name].append(value)
    return result


noon = datetime.time(12, 0)
today = datetime.date.today()
today_noon = datetime.datetime.combine(today, noon).astimezone(
    pytz.timezone(settings.TIME_ZONE)
)
tomorrow = today + datetime.timedelta(days=1)
tomorrow_noon = datetime.datetime.combine(tomorrow, noon).astimezone(
    pytz.timezone(settings.TIME_ZONE)
)
long_ago = today - datetime.timedelta(days=180)
long_ago_noon = datetime.datetime.combine(long_ago, noon).astimezone(
    pytz.timezone(settings.TIME_ZONE)
)


class MigrationsTestCase(TransactionTestCase):
    @property
    def app(self):
        return apps.get_containing_app_config(type(self).__module__).name

    migrate_from = None
    migrate_to = None

    def setUp(self):
        assert (
            self.migrate_from and self.migrate_to
        ), "TestCase '{}' must define migrate_from and migrate_to properties".format(
            type(self).__name__
        )
        self.migrate_from = [(self.app, self.migrate_from)]
        self.migrate_to = [(self.app, self.migrate_to)]
        executor = MigrationExecutor(connection)
        old_apps = executor.loader.project_state(self.migrate_from).apps

        # Reverse to the original migration
        executor.migrate(self.migrate_from)

        self.setUpBeforeMigration(old_apps)

        # Run the migration to test
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()  # reload.
        executor.migrate(self.migrate_to)

        self.apps = executor.loader.project_state(self.migrate_to).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes(self.app))

    def setUpBeforeMigration(self, apps):
        pass


# example
"""
class TestRemoveNullsMigrations(MigrationsTestCase):
    migrate_from = '0007_add_prize_key'
    migrate_to = '0008_remove_prize_nulls'

    def setUpBeforeMigration(self, apps):
        Prize = apps.get_model('tracker', 'Prize')
        Event = apps.get_model('tracker', 'Event')
        self.event = Event.objects.create(
            short='test', name='Test Event', datetime=today_noon, targetamount=100
        )
        self.prize1 = Prize.objects.create(event=self.event, name='Test Prize')

    def test_nulls_removed(self):
        self.prize1.refresh_from_db()
        self.assertEqual(self.prize1.altimage, '')
        self.assertEqual(self.prize1.description, '')
        self.assertEqual(self.prize1.extrainfo, '')
        self.assertEqual(self.prize1.image, '')
"""


class APITestCase(TransactionTestCase):
    model_name = None
    encoder = DjangoJSONEncoder()

    def parseJSON(self, response, status_code=200):
        self.assertEqual(
            response.status_code,
            status_code,
            msg='Status code is not %d\n"""%s"""' % (status_code, response.content),
        )
        try:
            return json.loads(response.content)
        except Exception as e:
            raise AssertionError(
                'Could not parse json: %s\n"""%s"""' % (e, response.content)
            )

    def assertModelPresent(self, expected_model, data, partial=False):
        found_model = next(
            (
                m
                for m in data
                if m['pk'] == expected_model['pk']
                and m['model'] == expected_model['model']
            ),
            None,
        )
        if not found_model:
            raise AssertionError(
                'Could not find model "%s:%s" in data'
                % (expected_model['model'], expected_model['pk'])
            )
        if partial:
            extra_keys = []
        else:
            extra_keys = set(found_model['fields']) - set(expected_model['fields'])
        missing_keys = set(expected_model['fields']) - set(found_model['fields'])
        unequal_keys = [
            k
            for k in expected_model['fields']
            if k in found_model['fields']
            and found_model['fields'][k] != expected_model['fields'][k]
        ]
        problems = (
            ['Extra key: "%s"' % k for k in extra_keys]
            + ['Missing key: "%s"' % k for k in missing_keys]
            + [
                'Value for key "%s" unequal: expected %r != actual %r'
                % (k, expected_model['fields'][k], found_model['fields'][k])
                for k in unequal_keys
            ]
        )
        if problems:
            raise AssertionError(
                'Model "%s:%s" was incorrect:\n%s'
                % (expected_model['model'], expected_model['pk'], '\n'.join(problems))
            )

    def assertModelNotPresent(self, unexpected_model, data):
        found_model = None
        for model in data:
            if (
                model['pk'] == unexpected_model['pk']
                and model['model'] == unexpected_model['model']
            ):
                found_model = model
                break
        if not found_model:
            raise AssertionError(
                'Found model "%s:%s" in data'
                % (unexpected_model['model'], unexpected_model['pk'])
            )

    def setUp(self):
        self.rand = random.Random()
        self.factory = RequestFactory()
        self.locked_event = models.Event.objects.create(
            datetime=long_ago_noon, targetamount=5, short='locked', name='Locked Event'
        )
        self.event = models.Event.objects.create(
            datetime=today_noon, targetamount=5, short='event', name='Test Event'
        )
        self.anonymous_user = AnonymousUser()
        self.user = User.objects.create(username='test')
        self.add_user = User.objects.create(username='add')
        self.locked_user = User.objects.create(username='locked')
        self.locked_user.user_permissions.add(
            Permission.objects.get(name='Can edit locked events')
        )
        if self.model_name:
            self.add_user.user_permissions.add(
                Permission.objects.get(name='Can add %s' % self.model_name),
                Permission.objects.get(name='Can change %s' % self.model_name),
            )
            self.locked_user.user_permissions.add(
                Permission.objects.get(name='Can add %s' % self.model_name),
                Permission.objects.get(name='Can change %s' % self.model_name),
            )
        self.super_user = User.objects.create(username='super', is_superuser=True)
        self.maxDiff = None


class ChangeSignalsTestMixin:
    def assertExpectedResultsPresent(self, expected, actual):
        missing_models = []
        missing_changes = []
        actual_model_changes = {}
        for actual_model, actual_changes in itertools.chain.from_iterable(
            result[1].get('changes', []) for result in actual
        ):
            actual_model_changes.setdefault(actual_model, []).extend(actual_changes)
        for expected_model, expected_changes in expected.get('changes', []):
            if expected_model not in actual_model_changes:
                missing_models.append(expected_model)
                continue
            for expected_change in expected_changes:
                if expected_change not in actual_model_changes[expected_model]:
                    missing_changes.append((expected_model, expected_change))

        self.assertEqual(
            len(missing_models),
            0,
            msg='\n'.join(
                f'Could not find model at all: {model}' for model in missing_models
            ),
        )
        self.assertEqual(
            len(missing_changes),
            0,
            msg='\n'.join(
                f'Could not find change for model: {model}, {change}'
                for model, change in missing_changes
            ),
        )
