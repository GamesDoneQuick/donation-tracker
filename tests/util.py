import datetime
import functools
import itertools
import json
import logging
import os
import random
import sys
import time
import unittest

from django.contrib.auth.models import AnonymousUser, Permission, User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Q
from django.test import RequestFactory, TransactionTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from tracker import models, settings
from tracker.api.pagination import TrackerPagination
from tracker.compat import zoneinfo


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
    zoneinfo.ZoneInfo(settings.TIME_ZONE)
)
tomorrow = today + datetime.timedelta(days=1)
tomorrow_noon = datetime.datetime.combine(tomorrow, noon).astimezone(
    zoneinfo.ZoneInfo(settings.TIME_ZONE)
)
long_ago = today - datetime.timedelta(days=180)
long_ago_noon = datetime.datetime.combine(long_ago, noon).astimezone(
    zoneinfo.ZoneInfo(settings.TIME_ZONE)
)


# TODO: remove this when 3.11 is oldest supported version
def parse_time(value):
    if sys.version_info < (3, 11):
        import dateutil.parser

        return dateutil.parser.parse(value)
    else:
        return datetime.datetime.fromisoformat(value)


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
    view_user_permissions = []  # trickles to add_user and locked_user
    add_user_permissions = []  # trickles to locked_user
    locked_user_permissions = []
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

    def get_detail(
        self,
        obj,
        *,
        model_name=None,
        status_code=200,
        data=None,
        kwargs=None,
        **other_kwargs,
    ):
        kwargs = kwargs or {}
        if 'user' in other_kwargs:
            self.client.force_authenticate(user=other_kwargs['user'])
        model_name = model_name or self.model_name
        assert model_name is not None
        response = self.client.get(
            reverse(
                f'tracker:api_v2:{model_name}-detail', kwargs={'pk': obj.pk, **kwargs}
            ),
            data=data,
        )
        self.assertEqual(
            response.status_code,
            status_code,
            msg=f'Expected status_code of {status_code}',
        )
        return getattr(response, 'data', None)

    def get_list(
        self,
        *,
        model_name=None,
        status_code=200,
        data=None,
        kwargs=None,
        **other_kwargs,
    ):
        kwargs = kwargs or {}
        if 'user' in other_kwargs:
            self.client.force_authenticate(user=other_kwargs['user'])
        model_name = model_name or self.model_name
        assert model_name is not None
        response = self.client.get(
            reverse(
                f'tracker:api_v2:{model_name}-list',
                kwargs=kwargs,
            ),
            data=data,
        )
        self.assertEqual(
            response.status_code,
            status_code,
            msg=f'Expected status_code of {status_code}',
        )
        return getattr(response, 'data', None)

    def get_noun(
        self,
        noun,
        obj=None,
        *,
        model_name=None,
        status_code=200,
        data=None,
        kwargs=None,
        **other_kwargs,
    ):
        kwargs = kwargs or {}
        if obj is not None:
            kwargs['pk'] = obj.pk
        if 'user' in other_kwargs:
            self.client.force_authenticate(user=other_kwargs['user'])
        model_name = model_name or self.model_name
        assert model_name is not None
        response = self.client.get(
            reverse(
                f'tracker:api_v2:{model_name}-{noun}',
                kwargs=kwargs,
            ),
            data=data,
        )
        self.assertEqual(
            response.status_code,
            status_code,
            msg=f'Expected status_code of {status_code}',
        )
        return getattr(response, 'data', None)

    def post_new(
        self,
        *,
        model_name=None,
        status_code=201,
        data=None,
        kwargs=None,
        **other_kwargs,
    ):
        return self.post_noun(
            'list',
            model_name=model_name,
            status_code=status_code,
            data=data,
            kwargs=kwargs,
            **other_kwargs,
        )

    def post_noun(
        self,
        noun,
        *,
        model_name=None,
        status_code=200,
        data=None,
        kwargs=None,
        **other_kwargs,
    ):
        kwargs = kwargs or {}
        data = data or {}
        if 'user' in other_kwargs:
            self.client.force_authenticate(user=other_kwargs['user'])
        model_name = model_name or self.model_name
        assert model_name is not None
        response = self.client.post(
            reverse(
                f'tracker:api_v2:{model_name}-{noun}',
                kwargs=kwargs,
            ),
            data=data,
        )
        self.assertEqual(
            response.status_code,
            status_code,
            msg=f'Expected status_code of {status_code}',
        )
        return getattr(response, 'data', None)

    def patch_detail(
        self,
        obj,
        *,
        model_name=None,
        status_code=200,
        data=None,
        kwargs=None,
        **other_kwargs,
    ):
        kwargs = kwargs or {}
        if 'user' in other_kwargs:
            self.client.force_authenticate(user=other_kwargs['user'])
        model_name = model_name or self.model_name
        assert model_name is not None
        response = self.client.patch(
            reverse(
                f'tracker:api_v2:{model_name}-detail', kwargs={'pk': obj.pk, **kwargs}
            ),
            data=data,
        )
        self.assertEqual(
            response.status_code,
            status_code,
            msg=f'Expected status_code of {status_code}',
        )
        return getattr(response, 'data', None)

    def _compare_value(self, expected, found):
        if expected == found:
            return True
        if not isinstance(expected, str) and isinstance(found, str):
            if isinstance(expected, datetime.datetime):
                if expected == parse_time(found):
                    return True
            else:
                try:
                    if expected == type(expected)(found):
                        return True
                except (TypeError, ValueError) as e:
                    logging.warning(
                        f'Could not parse value {found} as {type(expected)}', exc_info=e
                    )
        return False

    def _compare_model(self, expected_model, found_model, partial, prefix=''):
        if partial:
            extra_keys = []
        else:
            extra_keys = set(found_model.keys()) - set(expected_model.keys())
        missing_keys = set(expected_model.keys()) - set(found_model.keys())
        unequal_keys = [
            k
            for k in expected_model.keys()
            if k in found_model
            and not isinstance(found_model[k], (list, dict))
            and not self._compare_value(expected_model[k], found_model[k])
        ]
        nested_objects = [
            (
                f'{prefix}.' if prefix else '' + k,
                self._compare_model(
                    expected_model[k], found_model[k], partial, prefix=k
                ),
            )
            for k in expected_model.keys()
            if k in found_model and isinstance(found_model[k], dict)
        ]
        nested_objects = [n for n in nested_objects if n[1]]
        nested_list_keys = {
            f'{prefix}.'
            if prefix
            else ''
            + f'{k}': self._compare_lists(
                expected_model[k], found_model[k], partial, prefix=k
            )
            for k in expected_model.keys()
            if k in found_model and isinstance(found_model[k], list)
        }
        for k, v in nested_list_keys.items():
            for n, vn in enumerate(v):
                if vn:
                    nested_objects.append((f'{k}[{n}]', vn))
        return (
            *('Extra key: "%s"' % k for k in extra_keys),
            *('Missing key: "%s"' % k for k in missing_keys),
            *(
                'Value for key "%s" unequal: expected %r != actual %r'
                % (k, expected_model[k], found_model[k])
                for k in unequal_keys
            ),
            *('Nested object: %s, %s' % k for k in nested_objects),
        )

    def _compare_lists(self, expected, found, partial, prefix=''):
        results = []
        for n, pair in enumerate(itertools.zip_longest(expected, found)):
            if pair[0] is None:
                results.append(f'index #{n} was extra')
            elif pair[1] is None:
                results.append(f'index #{n} was missing')
            elif not isinstance(pair[1], type(pair[0])):
                results.append(
                    f'index #{n} had different types, `{type(pair[0])}` != `{type(pair[1])}`'
                )
            elif isinstance(pair[0], dict):
                results.append(self._compare_model(pair[0], pair[1], partial, prefix))
            elif pair[0] != pair[1]:
                results.append(f'index #{n} was unequal: {pair[0]:r} != {pair[1]:r}')
        return results

    def assertModelPresent(self, expected_model, data, partial=False, msg=None):
        try:
            found_model = next(
                model
                for model in data
                if (
                    model['pk'] == expected_model['pk']
                    and model['model'] == expected_model['model']
                )
            )
        except StopIteration:
            raise AssertionError(
                'Could not find model "%s:%s" in data'
                % (expected_model['model'], expected_model['pk'])
            )
        problems = self._compare_model(
            expected_model['fields'], found_model['fields'], partial
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
        with self.assertRaises(
            StopIteration,
            msg='Found model "%s:%s" in data'
            % (unexpected_model['model'], unexpected_model['pk']),
        ):
            next(
                model
                for model in data
                if (
                    model['pk'] == unexpected_model['pk']
                    and model['model'] == unexpected_model['model']
                )
            )

    def assertV2ModelPresent(self, expected_model, data, partial=False, msg=None):
        if not isinstance(data, list):
            data = [data]
        try:
            found_model = next(
                m
                for m in data
                if expected_model['type'] == m['type']
                and expected_model['id'] == m['id']
            )
        except StopIteration:
            raise AssertionError(
                'Could not find model "%s:%s" in data'
                % (expected_model['type'], expected_model['id'])
            )
        problems = self._compare_model(expected_model, found_model, partial)
        if problems:
            raise AssertionError(
                '%sModel "%s:%s" was incorrect:\n%s'
                % (
                    f'{msg}\n' if msg else '',
                    expected_model['type'],
                    expected_model['id'],
                    '\n'.join(problems),
                )
            )

    def assertV2ModelNotPresent(self, unexpected_model, data):
        with self.assertRaises(
            StopIteration,
            msg='Found model "%s:%s" in data'
            % (unexpected_model['type'], unexpected_model['id']),
        ):
            next(
                model
                for model in data
                if (
                    model['id'] == unexpected_model['id']
                    and model['type'] == unexpected_model['type']
                )
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
        self.client = APIClient()
        self.locked_event = models.Event.objects.create(
            datetime=long_ago_noon,
            targetamount=5,
            short='locked',
            name='Locked Event',
            locked=True,
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
            # TODO: unify codename use to get rid of the union
            view_perm = Permission.objects.get(
                Q(name=f'Can view {self.model_name}')
                | Q(codename=f'view_{self.model_name}')
            )
            change_perm = Permission.objects.get(
                Q(name=f'Can change {self.model_name}')
                | Q(codename=f'change_{self.model_name}')
            )
            add_perm = Permission.objects.get(
                Q(name=f'Can add {self.model_name}')
                | Q(codename=f'add_{self.model_name}')
            )
            self.view_user.user_permissions.add(view_perm)
            self.add_user.user_permissions.add(
                view_perm,
                change_perm,
                add_perm,
            )
            self.locked_user.user_permissions.add(
                view_perm,
                change_perm,
                add_perm,
            )
        permissions = Permission.objects.filter(codename__in=self.view_user_permissions)
        assert permissions.count() == len(
            self.view_user_permissions
        ), 'permission code mismatch'
        self.view_user.user_permissions.add(*permissions)
        permissions |= Permission.objects.filter(codename__in=self.add_user_permissions)
        assert permissions.count() == len(
            set(self.view_user_permissions + self.add_user_permissions)
        ), 'permission code mismatch'
        self.add_user.user_permissions.add(*permissions)
        permissions |= Permission.objects.filter(
            codename__in=self.locked_user_permissions
        )
        assert permissions.count() == len(
            set(
                self.view_user_permissions
                + self.add_user_permissions
                + self.locked_user_permissions
            )
        ), 'permission code mismatch'
        self.locked_user.user_permissions.add(*permissions)
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
        if not bool(int(os.environ.get('TRACKER_DISABLE_HEADLESS', '0'))):
            options.add_argument('--headless')
        cls.webdriver = webdriver.Firefox(options=options)
        cls.webdriver.implicitly_wait(5)

    @classmethod
    def tearDownClass(cls):
        cls.webdriver.quit()
        super().tearDownClass()

    def tearDown(self):
        super().tearDown()
        self.tracker_logout()
        if self.test_failed:
            self.webdriver.get_screenshot_as_file(
                f'./test-results/TEST-{self.id()}.{int(time.time())}.png'
            )
            if not bool(int(os.environ.get('TRACKER_DISABLE_DUMP', '0'))):
                raise Exception(
                    f'{self.webdriver.current_url}\ndata:image/png;base64,{self.webdriver.get_screenshot_as_base64()}'
                )

    def tracker_login(self, username, password='password'):
        self.webdriver.get(self.live_server_url + reverse('admin:login'))
        self.webdriver.find_element(By.NAME, 'username').send_keys(username)
        self.webdriver.find_element(By.NAME, 'password').send_keys(password)
        self.webdriver.find_element(By.CSS_SELECTOR, 'form input[type=submit]').click()
        self.webdriver.find_element(
            By.CSS_SELECTOR, '.app-tracker'
        )  # admin page has loaded

    def tracker_logout(self):
        self.webdriver.delete_cookie(settings.SESSION_COOKIE_NAME)

    def select_option(self, selector, value):
        Select(self.webdriver.find_element(By.CSS_SELECTOR, selector)).select_by_value(
            value
        )

    def wait_for_spinner(self):
        WebDriverWait(self.webdriver, 5).until_not(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-test-id="spinner"]')
            )
        )
