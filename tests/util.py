import datetime
import functools
import json
import random
import time
import unittest

import pytz
from django.contrib.auth.models import AnonymousUser, Permission, User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import RequestFactory, TransactionTestCase, override_settings
from django.urls import reverse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from tracker import models, settings
from tracker.api.pagination import TrackerPagination


def parse_test_mail(mail):
    lines = [
        x.partition(':')
        for x in [x for x in [x.strip() for x in mail.message.split('\n')] if x]
    ]
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
    # e.g
    # migrate_from = [('tracker', '0004_add_thing')]
    # migrate_to = [('tracker', '0005_backfill_thing')]
    migrate_from = []
    migrate_to = []

    def setUp(self):
        assert (
            self.migrate_from and self.migrate_to
        ), "TestCase '{}' must define migrate_from and migrate_to properties".format(
            type(self).__name__
        )
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
        executor.migrate(executor.loader.graph.leaf_nodes())

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
            ) from e

    def get_paginated_response(self, queryset, data):
        paginator = TrackerPagination()

        class FakeRequest:
            def __init__(self, limit=settings.TRACKER_PAGINATION_LIMIT, offset=0):
                self.query_params = {'limit': limit, 'offset': offset}

        paginator.paginate_queryset(queryset, FakeRequest())
        return paginator.get_paginated_response(data)

    def assertModelPresent(self, expected_model, data, partial=False, msg=None):
        found_model = None
        for model in data:
            if (
                model['pk'] == expected_model['pk']
                and model['model'] == expected_model['model']
            ):
                found_model = model
                break
        if not found_model:
            raise AssertionError(
                'Could not find model "%s:%s" in data'
                % (expected_model['model'], expected_model['pk'])
            )
        if partial:
            extra_keys = []
        else:
            extra_keys = set(found_model['fields'].keys()) - set(
                expected_model['fields'].keys()
            )
        missing_keys = set(expected_model['fields'].keys()) - set(
            found_model['fields'].keys()
        )
        unequal_keys = [
            k
            for k in expected_model['fields'].keys()
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
                '%sModel "%s:%s" was incorrect:\n%s'
                % (
                    f'{msg}\n' if msg else '',
                    expected_model['model'],
                    expected_model['pk'],
                    '\n'.join(problems),
                )
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

    def assertLogEntry(self, model_name: str, pk: int, change_type, message: str):
        from django.contrib.admin.models import LogEntry

        entry = LogEntry.objects.filter(
            content_type__model__iexact=model_name,
            action_flag=change_type,
            object_id=pk,
        ).first()

        self.assertIsNotNone(entry, msg='Could not find log entry')
        self.assertEqual(entry.change_message, message)

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
        self.view_user = User.objects.create(username='view')
        self.add_user = User.objects.create(username='add')
        self.locked_user = User.objects.create(username='locked')
        self.locked_user.user_permissions.add(
            Permission.objects.get(name='Can edit locked events')
        )
        if self.model_name:
            self.view_user.user_permissions.add(
                Permission.objects.get(name=f'Can view {self.model_name}'),
            )
            self.add_user.user_permissions.add(
                Permission.objects.get(name=f'Can add {self.model_name}'),
                Permission.objects.get(name=f'Can change {self.model_name}'),
                Permission.objects.get(name=f'Can view {self.model_name}'),
            )
            self.locked_user.user_permissions.add(
                Permission.objects.get(name=f'Can add {self.model_name}'),
                Permission.objects.get(name=f'Can change {self.model_name}'),
                Permission.objects.get(name=f'Can view {self.model_name}'),
            )
        self.super_user = User.objects.create(username='super', is_superuser=True)
        self.maxDiff = None


def _tag_error(func):
    """Decorates a unittest test function to add failure information to the TestCase."""

    @functools.wraps(func)
    def decorator(self, *args, **kwargs):
        """Add failure information to `self` when `func` raises an exception."""
        self.test_failed = False
        try:
            func(self, *args, **kwargs)
        except unittest.SkipTest:
            raise
        except Exception:  # pylint: disable=broad-except
            self.test_failed = True
            raise  # re-raise the error with the original traceback.

    return decorator


class _TestFailedMeta(type):
    """Metaclass to decorate test methods to append error information to the TestCase instance."""

    def __new__(mcs, name, bases, dct):
        for name, prop in dct.items():
            # assume that TestLoader.testMethodPrefix hasn't been messed with -- otherwise, we're hosed.
            if name.startswith('test') and callable(prop):
                dct[name] = _tag_error(prop)

        return super().__new__(mcs, name, bases, dct)


@override_settings(DEBUG=True)
class TrackerSeleniumTestCase(StaticLiveServerTestCase, metaclass=_TestFailedMeta):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        options = Options()
        options.headless = True
        cls.webdriver = webdriver.Firefox(options=options)
        cls.webdriver.implicitly_wait(5)

    @classmethod
    def tearDownClass(cls):
        cls.webdriver.quit()
        super().tearDownClass()

    def tearDown(self):
        super().tearDown()
        if self.test_failed:
            self.webdriver.get_screenshot_as_file(
                f'./test-results/TEST-{self.id()}.{int(time.time())}.png'
            )
            raise Exception(
                f'data:image/png;base64,{self.webdriver.get_screenshot_as_base64()}'
            )

    def tracker_login(self, username, password='password'):
        self.webdriver.get(self.live_server_url + reverse('admin:login'))
        self.webdriver.find_element_by_name('username').send_keys(username)
        self.webdriver.find_element_by_name('password').send_keys(password)
        self.webdriver.find_element_by_css_selector('form input[type=submit]').click()
        self.webdriver.find_element_by_css_selector(
            '.app-tracker'
        )  # admin page has loaded

    def tracker_logout(self):
        self.webdriver.get(self.live_server_url + reverse('admin:logout'))
        self.assertEqual(
            self.webdriver.find_element_by_css_selector('#content h1').text,
            'Logged out',
        )

    def select_option(self, selector, value):
        Select(self.webdriver.find_element_by_css_selector(selector)).select_by_value(
            value
        )

    def wait_for_spinner(self):
        WebDriverWait(self.webdriver, 5).until_not(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-test-id="spinner"]')
            )
        )
