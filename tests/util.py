import contextlib
import csv
import datetime
import functools
import io
import itertools
import json
import logging
import os
import random
import re
import sys
import time
import unittest
from decimal import Decimal

from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import AnonymousUser, Permission, User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Q
from django.test import RequestFactory, TransactionTestCase, override_settings
from django.urls import reverse
from paypal.standard.ipn.models import PayPalIPN
from rest_framework.exceptions import ErrorDetail
from rest_framework.serializers import ModelSerializer
from rest_framework.test import APIClient
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from tracker import models, settings, util
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


def parse_csv_response(response):
    assert response['content-type'].startswith(
        'text/csv'
    ), f'expected `text/csv` for content-type, got {response["content-type"]}'
    return [
        line
        for line in csv.reader(io.StringIO(response.content.decode(response.charset)))
    ]


def create_ipn(
    donation,
    email,
    *,
    residence_country='US',
    custom=None,
    payment_status='Completed',
    mc_currency='USD',
    mc_gross=None,
    mc_fee=None,
    txn_id='deadbeef',
    **kwargs,
):
    mc_fee = mc_fee if mc_fee is not None else donation.amount * Decimal('0.03')
    mc_gross = mc_gross if mc_gross is not None else donation.amount
    custom = custom if custom is not None else f'{donation.id}:{donation.domainId}'
    return PayPalIPN.objects.create(
        residence_country=residence_country,
        mc_currency=mc_currency,
        mc_gross=mc_gross,
        custom=custom,
        payment_status=payment_status,
        payer_email=email,
        mc_fee=mc_fee,
        txn_id=txn_id,
        **kwargs,
    )


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

    def permissions_helper(self, user, group, old, new, forwards):
        from django.contrib.auth.models import Permission

        new = Permission.objects.get(
            content_type__app_label=new['app_label'],
            content_type__model=new['model'],
            codename=new['codename'],
        )
        self.assertIn(
            user,
            new.user_set.all(),
            msg=f'User did not have {"new" if forwards else "old"} permission',
        )
        self.assertIn(
            group,
            new.group_set.all(),
            msg=f'Group did not have {"new" if forwards else "old"} permission',
        )
        self.assertFalse(
            Permission.objects.filter(
                content_type__app_label=old['app_label'],
                content_type__model=old['model'],
                codename=old['codename'],
            ).exists(),
            msg=f'Did not delete {"old" if forwards else "new"} permission on {"forwards" if forwards else "backwards"} migration',
        )


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


class AssertionHelpers:
    def assertDictContainsSubset(self, subset, dictionary, msg=None):
        if sys.version_info < (3, 12):
            super().assertDictContainsSubset(subset, dictionary, msg)
        else:
            self.assertEqual(dictionary, {**dictionary, **subset}, msg)

    def assertSetDisjoint(self, set1, set2, msg=None):
        self.assertSetEqual(set(set1) & set(set2), set(), msg)

    def assertSubset(self, sub, sup, msg=None):
        self.assertSetEqual(set(sub) & set(sup), set(sub), msg)


class APITestCase(TransactionTestCase, AssertionHelpers):
    fixtures = ['countries']
    model_name = None
    serializer_class = None
    format_model = None
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

    def _get_viewname(self, model_name, action, **kwargs):
        if 'event_pk' in kwargs:
            if 'feed' in kwargs:
                viewname = f'tracker:api_v2:event-{model_name}-feed-{action}'
            else:
                viewname = f'tracker:api_v2:event-{model_name}-{action}'
        else:
            viewname = f'tracker:api_v2:{model_name}-{action}'
        return viewname

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
        pk = obj if isinstance(obj, int) else obj.pk
        url = reverse(
            self._get_viewname(model_name, 'detail', **kwargs),
            kwargs={'pk': pk, **kwargs},
        )
        with self._snapshot('GET', url, data) as snapshot:
            response = self.client.get(
                url,
                data=data,
            )
            self.assertEqual(
                response.status_code,
                status_code,
                msg=f'Expected status_code of {status_code}',
            )
            snapshot.process_response(response)
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
        url = reverse(
            self._get_viewname(model_name, 'list', **kwargs),
            kwargs=kwargs,
        )
        with self._snapshot('GET', url, data) as snapshot:
            response = self.client.get(
                url,
                data=data,
            )
            self.assertEqual(
                response.status_code,
                status_code,
                msg=f'Expected status_code of {status_code}',
            )
            snapshot.process_response(response)
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
        url = reverse(self._get_viewname(model_name, noun, **kwargs), kwargs=kwargs)
        with self._snapshot('GET', url, data) as snapshot:
            response = self.client.get(
                url,
                data=data,
            )
            self.assertEqual(
                response.status_code,
                status_code,
                msg=f'Expected status_code of {status_code}',
            )
            snapshot.process_response(response)
        return getattr(response, 'data', None)

    def _check_nested_codes(self, data, codes):
        mismatched_codes = {}
        if not isinstance(data, (list, dict, ErrorDetail)):
            raise TypeError(f'Expected list, dict, or ErrorDetail, got {type(data)}')
        if isinstance(data, ErrorDetail):
            data = [data]
        if isinstance(data, list):
            # FIXME: this comes up if, for example, one entry in an M2M is valid
            #  but the others are not, but there isn't a test case that exercises this
            #  in depth just yet
            data = [d for d in data if d]
            if data and isinstance(data[0], dict):
                mismatch = {}
                for d in data:
                    mismatch = self._check_nested_codes(d, codes) or mismatch
                return mismatch
            else:
                data = list(util.flatten(data))
                if any(not isinstance(d, ErrorDetail) for d in data):
                    raise TypeError('Expected a list of ErrorDetail')
        if isinstance(codes, (list, str)):
            if isinstance(codes, str):
                codes = [codes]
            if isinstance(data, dict):
                data = list(util.flatten_dict(data))
            elif not isinstance(data, list):
                raise TypeError(f'Expected list or dict, got {type(data)}')
            actual_codes = {e.code for e in data}
            for code in codes:
                if code not in actual_codes:
                    mismatched_codes.setdefault('__any__', []).append(code)
        elif isinstance(codes, dict):
            if isinstance(data, list):
                for d in data:
                    mismatched_codes.update(self._check_nested_codes(d, codes))
            elif isinstance(data, dict):
                for field, code in codes.items():
                    nested = self._check_nested_codes(data.get(field, []), code)
                    if nested:
                        nested.pop('__any__', [])
                        mismatched_codes.setdefault(field, []).append(code)
        else:
            raise TypeError(f'Expected list, str, or dict, got {type(codes)}')
        return mismatched_codes

    def _check_status_and_error_codes(
        self, response, status_code, expected_error_codes
    ):
        data = getattr(response, 'data', None)
        self.assertEqual(
            response.status_code,
            status_code,
            msg=f'Expected status_code of {status_code}'
            + ('\n' + str(data) if data else ''),
        )
        if data and expected_error_codes:
            # TODO: some of the failure messages are vague, figure out a better way to nest the formatting
            mismatched_codes = self._check_nested_codes(data, expected_error_codes)
            if mismatched_codes:
                self.fail(
                    '\n'.join(
                        f'expected error code for `{field}`: `{code}` not present in `{",".join((e.code if isinstance(e, ErrorDetail) else str(e)) for e in data.get(field, []))}`'
                        for field, code in mismatched_codes.items()
                    )
                )

    def post_new(
        self,
        *,
        model_name=None,
        status_code=201,
        data=None,
        kwargs=None,
        expected_error_codes=None,
        **other_kwargs,
    ):
        return self.post_noun(
            'list',
            model_name=model_name,
            status_code=status_code,
            data=data,
            kwargs=kwargs,
            expected_error_codes=expected_error_codes,
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
        expected_error_codes=None,
        **other_kwargs,
    ):
        kwargs = kwargs or {}
        data = data or {}
        if 'user' in other_kwargs:
            self.client.force_authenticate(user=other_kwargs['user'])
        model_name = model_name or self.model_name
        assert model_name is not None
        url = reverse(self._get_viewname(model_name, noun, **kwargs), kwargs=kwargs)
        with self._snapshot('POST', url, data) as snapshot:
            response = self.client.post(
                url,
                data=data,
                format='json',
            )
            self._check_status_and_error_codes(
                response, status_code, expected_error_codes or {}
            )
            snapshot.process_response(response)
        return getattr(response, 'data', None)

    def patch_detail(
        self,
        obj,
        *,
        model_name=None,
        status_code=200,
        expected_error_codes=None,
        data=None,
        kwargs=None,
        **other_kwargs,
    ):
        kwargs = kwargs or {}
        if 'user' in other_kwargs:
            self.client.force_authenticate(user=other_kwargs['user'])
        model_name = model_name or self.model_name
        assert model_name is not None
        url = reverse(
            self._get_viewname(model_name, 'detail', **kwargs),
            kwargs={'pk': obj.pk, **kwargs},
        )
        if status_code >= 400 and not expected_error_codes:
            # just a debug point to make an exhaustive pass on this later
            pass
        with self._snapshot('PATCH', url, data) as snapshot:
            response = self.client.patch(
                url,
                data=data,
                format='json',
            )
            self._check_status_and_error_codes(
                response, status_code, expected_error_codes or {}
            )
            snapshot.process_response(response)
        obj.refresh_from_db()
        return getattr(response, 'data', None)

    def _compare_value(self, key, expected, found):
        if expected == found:
            return True
        if key.endswith(
            'canonical_url'
        ):  # special case, so we don't have to pass the request object around
            length = min(len(expected), len(found))
            return expected[-length:] == found[-length:]
        if not isinstance(expected, str) and isinstance(found, str):
            if isinstance(expected, datetime.datetime):
                if expected == util.parse_time(found):
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

    def _compare_model(
        self, expected_model, found_model, partial, prefix='', *, missing_ok=None
    ):
        missing_ok = missing_ok or []
        self.assertIsInstance(found_model, dict, 'found_model was not a dict')
        self.assertIsInstance(expected_model, dict, 'expected_model was not a dict')
        if partial:
            extra_keys = []
        else:
            extra_keys = set(found_model.keys()) - set(expected_model.keys())
        missing_keys = (
            set(expected_model.keys()) - set(found_model.keys()) - set(missing_ok)
        )
        unequal_keys = [
            k
            for k in expected_model.keys()
            if k in found_model
            and not isinstance(found_model[k], (list, dict))
            and not self._compare_value(k, expected_model[k], found_model[k])
        ]
        nested_objects = [
            (
                f'{prefix}.' if prefix else '' + k,
                self._compare_model(
                    expected_model[k],
                    found_model[k],
                    partial,
                    prefix=k,
                    missing_ok=missing_ok,
                ),
            )
            for k in expected_model.keys()
            if k in found_model and isinstance(found_model[k], dict)
        ]
        nested_objects = [n for n in nested_objects if n[1]]
        nested_list_keys = {
            f'{prefix}.' if prefix else '' + f'{k}': self._compare_lists(
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

    def assertModelPresent(
        self, expected_model, data, partial=False, msg=None, format_kwargs=None
    ):
        if not isinstance(data, list):
            data = [data]
        if not isinstance(expected_model, dict):
            assert (
                self.format_model is not None
            ), 'no format_model provided and raw model was passed to assertModelPresent'
            expected_model = self.format_model(expected_model, **format_kwargs or {})
        if (
            found_model := next(
                (
                    model
                    for model in data
                    if (
                        model['pk'] == expected_model['pk']
                        and model['model'] == expected_model['model']
                    )
                ),
                None,
            )
        ) is None:
            self.fail(
                'Could not find model "%s:%s" in data'
                % (expected_model['model'], expected_model['pk'])
            )
        problems = self._compare_model(
            expected_model['fields'], found_model['fields'], partial
        )
        if problems:
            self.fail(
                '%sModel "%s:%s" was incorrect:\n%s'
                % (
                    f'{msg}\n' if msg else '',
                    expected_model['model'],
                    expected_model['pk'],
                    '\n'.join(problems),
                )
            )

    def assertModelNotPresent(
        self, unexpected_model, data, msg=None, format_kwargs=None
    ):
        if not isinstance(data, list):
            data = [data]
        if not isinstance(unexpected_model, dict):
            assert (
                self.format_model is not None
            ), 'no format_model provided and raw model was passed to assertModelNotPresent'
            unexpected_model = self.format_model(
                unexpected_model, **format_kwargs or {}
            )
        if (
            next(
                (
                    model
                    for model in data
                    if (
                        model['pk'] == unexpected_model['pk']
                        and model['model'] == unexpected_model['model']
                    )
                ),
                None,
            )
            is not None
        ):
            self.fail(
                '%sFound model "%s:%s" in data'
                % (
                    '%s\n' if msg else '',
                    unexpected_model['model'],
                    unexpected_model['pk'],
                )
            )

    def assertV2ModelPresent(
        self, expected_model, data, *, serializer_kwargs=None, partial=False, msg=None
    ):
        """
        expected_model is either a dict (e.g. from a serializer), or a raw model (in which case you can pass
        serializier_kwargs to pass extra arguments to the serializer), data is whatever came back to the api,
        either a single model or a list of models, and asserts that not only is a matching model present, but that
        it has the same representation
        if partial is True, then extra keys in data are ok, but not missing or mismatched keys
        if missing_ok has any values, then those explicit keys are allowed to be missing, but not unequal (useful for
         nested models)
        """
        if not isinstance(data, list):
            data = [data]
        missing_ok = []
        if isinstance(expected_model, ModelSerializer):
            expected_model = expected_model.data
        elif not isinstance(expected_model, dict):
            assert (
                self.serializer_class is not None
            ), 'no serializer_class provided and raw model was passed'
            expected_model.refresh_from_db()
            expected_model = self.serializer_class(
                expected_model, **serializer_kwargs or {}
            ).data
            # FIXME: gross hack
            from tracker.api.serializers import EventNestedSerializerMixin

            if issubclass(self.serializer_class, EventNestedSerializerMixin):
                missing_ok.append('event')
        if (
            found_model := next(
                (
                    m
                    for m in data
                    if expected_model['type'] == m['type']
                    and expected_model['id'] == m['id']
                ),
                None,
            )
        ) is None:
            self.fail(
                'Could not find model "%s:%s" in data'
                % (expected_model['type'], expected_model['id'])
            )
        problems = self._compare_model(
            expected_model, found_model, partial, missing_ok=missing_ok
        )
        if problems:
            self.fail(
                '%sModel "%s:%s" was incorrect:\n%s'
                % (
                    f'{msg}\n' if msg else '',
                    expected_model['type'],
                    expected_model['id'],
                    '\n'.join(problems),
                )
            )

    def assertV2ModelNotPresent(self, unexpected_model, data):
        if isinstance(unexpected_model, ModelSerializer):
            unexpected_model = unexpected_model.data
        elif not isinstance(unexpected_model, dict):
            assert hasattr(
                self, 'serializer_class'
            ), 'no serializer_class provided and raw model was passed'
            unexpected_model = self.serializer_class(unexpected_model).data
        if (
            next(
                (
                    model
                    for model in data
                    if (
                        model['id'] == unexpected_model['id']
                        and model['type'] == unexpected_model['type']
                    )
                ),
                None,
            )
            is not None
        ):
            self.fail(
                'Found model "%s:%s" in data'
                % (unexpected_model['type'], unexpected_model['id'])
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

    @contextlib.contextmanager
    def assertLogsChanges(self, number, action_flag=None):
        q = LogEntry.objects
        if action_flag:
            q = q.filter(action_flag=action_flag)
        before = q.count()
        yield
        after = q.count()
        self.assertEqual(
            before + number,
            after,
            msg=f'Expected {number} change(s) logged, got {after - before}',
        )

    @contextlib.contextmanager
    def saveSnapshot(self):
        # TODO: don't save 'empty' results by default?
        assert getattr(self, '_save_snapshot', False) is False, 'no nesting this yet'
        self._save_snapshot = True
        self._last_subtest = None
        try:
            yield
        finally:
            self._save_snapshot = False

    class _Snapshot:
        def __init__(self, url, method, data=None, stream=None):
            self.url = url
            self.method = method
            self.data = data
            self.stream = stream

        def process_response(self, response):
            if self.stream:
                obj = {
                    'request': {'url': self.url, 'method': self.method},
                    'response': {
                        'status_code': response.status_code,
                        'data': response.json(),
                    },
                }
                if self.data is not None:
                    obj['request']['data'] = self.data
                json.dump(obj, self.stream, indent=True, cls=DjangoJSONEncoder)

    @contextlib.contextmanager
    def _snapshot(self, method, url, data):
        if self._save_snapshot:
            # TODO: replace with removeprefix when 3.8 is no longer supported
            pieces = [
                re.sub(
                    r'^tests\.',
                    '',
                    re.sub(r'^donation-tracker\.', '', self.__class__.__module__),
                ).replace('.', '_'),
                re.sub(r'^Test', '', self.__class__.__name__),
                re.sub(r'^test_', '', self._testMethodName).lower(),
            ]
            subtest = self
            while next_subtest := getattr(subtest, '_subtest', None):
                subtest = next_subtest
                if subtest._message == 'happy path':
                    continue
                pieces.append(re.sub(r'\W', '_', subtest._message).lower())

            if self._last_subtest is not subtest:
                self._snapshot_num = 1

            # obscure ids from url since they can drift depending on test order/results, remove leading tracker since it's redundant, and slugify everything else
            pieces += [
                f'S{self._snapshot_num}',
                re.sub(
                    r'\W', '_', re.sub(r'^/tracker', '', re.sub(r'/\d+/', '/pk/', url))
                ),
                method,
            ]

            snapshot_name = '_'.join(p.strip('_') for p in pieces)
            self._snapshot_num += 1
            self._last_subtest = subtest

            basepath = os.path.join(os.path.dirname(__file__), 'snapshots')
            os.makedirs(basepath, exist_ok=True)
            with open(os.path.join(basepath, f'{snapshot_name}.json'), 'w') as stream:
                yield APITestCase._Snapshot(url, method, data, stream)
        else:
            yield APITestCase._Snapshot(url, method)

    def setUp(self):
        super().setUp()
        self._save_snapshot = False
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
        self.blank_event = models.Event.objects.create(
            datetime=tomorrow_noon,
            targetamount=5,
            short='blank',
            name='Blank Event',
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
