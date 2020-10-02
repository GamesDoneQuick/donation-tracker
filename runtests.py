#!/usr/bin/env python
import os
import sys
import logging
import json
from argparse import ArgumentParser
from subprocess import check_call

import django
from django.conf import settings
from django.test.utils import get_runner
from celery import Celery

# needs additional dependencies
# pip install -r tests/requirements.txt
# must be run from the tracker root folder, for now

if __name__ == '__main__':
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_settings'
    django.setup()
    app = Celery()
    app.config_from_object(
        {'task_always_eager': True,}
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
    parser.add_argument(
        '--failfast',
        action='store_true',
        dest='failfast',
        default=False,
        help='Tells Django to stop running the test suite after first failed test.',
    )
    # TODO: the fetches for the ui endpoints blow up if the manifest doesn't exist so we have to build the webpack bundles first
    try:
        json.load(open('tracker/ui-tracker.manifest.json'))['files']['tracker']
    except (IOError, KeyError):
        check_call(['yarn', '--frozen-lockfile', '--production'])
        check_call(['yarn', 'build'])
    TestRunner = get_runner(settings, 'xmlrunner.extra.djangotestrunner.XMLTestRunner')
    TestRunner.add_arguments(parser)
    test_runner = TestRunner(**parser.parse_args(sys.argv[1:]).__dict__)
    failures = test_runner.run_tests(['tests'])

    sys.exit(bool(failures))
