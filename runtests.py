#!/usr/bin/env python
import logging
import os
import subprocess
import sys
from argparse import ArgumentParser

import django
import requests
from celery import Celery
from django.conf import settings
from django.test.utils import get_runner

# needs additional dependencies
# pip install -r tests/requirements.txt
# must be run from the tracker root folder, for now

if __name__ == '__main__':
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_settings'
    django.setup()
    app = Celery()
    app.config_from_object(
        {
            'task_always_eager': True,
        }
    )
    logging.getLogger('post_office').disabled = True
    parser = ArgumentParser()
    # stolen from run test command
    parser.add_argument(
        'args',
        metavar='test_label',
        nargs='*',
        help='Module paths to test; can be modulename, modulename.TestCase or modulename.TestCase.test_method',
    )
    parser.add_argument(
        '--noinput',
        '--no-input',
        action='store_false',
        dest='interactive',
        default=True,
        help='Tells Django to NOT prompt the user for input of any kind.',
    )
    if django.VERSION < (5, 1, 0):
        parser.add_argument(
            '--failfast',
            action='store_true',
            dest='failfast',
            default=False,
            help='Tells Django to stop running the test suite after first failed test.',
        )
    parser.add_argument(
        '--nobundle',
        '--no-bundle',
        action='store_false',
        dest='bundle',
        default=True,
        help='Skips building the js bundles.',
    )
    parser.add_argument(
        '--skip-ts-check',
        action='store_false',
        dest='ts_check',
        default=True,
        help='Skips checking the Typescript definitions for API responses.',
    )
    parser.add_argument('-v', '--verbose', action='count', default=0, dest='verbosity')

    TestRunner = get_runner(settings, 'xmlrunner.extra.djangotestrunner.XMLTestRunner')
    TestRunner.add_arguments(parser)
    parsed = parser.parse_args(sys.argv[1:])
    test_runner = TestRunner(**parsed.__dict__)

    if parsed.bundle:
        try:
            # if webpack is already running then we don't need to build the bundles
            requests.get('http://localhost:8080/')
        except requests.ConnectionError:
            subprocess.check_call(['yarn', '--immutable'])
            subprocess.check_call(['yarn', 'build'])

    if parsed.ts_check:
        subprocess.check_call(['git', 'clean', '-fxd', 'tests/snapshots'])

    failures = test_runner.run_tests(parsed.args or ['tests'])

    if not failures and parsed.ts_check:
        from ts_api_check import ts_check

        print('Checking TypeScript API definitions...')

        if not ts_check():
            print('TypeScript API check failed, see logs for more details')
            failures += 1

    sys.exit(bool(failures))
