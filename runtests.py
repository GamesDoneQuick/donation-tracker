#!/usr/bin/env python
import os
import subprocess
import sys
import logging
from argparse import ArgumentParser

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
    try:
        subprocess.check_call(
            ['yarn', 'build'],
            env={**os.environ, 'NODE_ENV': 'development', 'NO_HMR': '1'},
        )
    except subprocess.SubprocessError:
        # maybe failed because the modules aren't installed
        subprocess.check_call(['yarn', '--frozen-lockfile', '--production'])
        subprocess.check_call(
            ['yarn', 'build'],
            env={**os.environ, 'NODE_ENV': 'development', 'NO_HMR': '1'},
        )
    TestRunner = get_runner(settings, 'xmlrunner.extra.djangotestrunner.XMLTestRunner')
    TestRunner.add_arguments(parser)
    parsed = parser.parse_args(sys.argv[1:])
    test_runner = TestRunner(**parsed.__dict__)
    failures = test_runner.run_tests(parsed.args or ['tests'])

    sys.exit(bool(failures))
