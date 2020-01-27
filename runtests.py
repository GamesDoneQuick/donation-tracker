#!/usr/bin/env python
import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner
from argparse import ArgumentParser

# needs additional dependencies
# tblib is needed for printing tracebacks on parallel runs
# pip install unittest-xml-reporting tblib
# must be run from the tracker root folder, for now

if __name__ == '__main__':
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_settings'
    # TODO: need to move tracker into a subfolder so this isn't necessary
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    django.setup()
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
    TestRunner = get_runner(settings, 'xmlrunner.extra.djangotestrunner.XMLTestRunner')
    TestRunner.add_arguments(parser)
    test_runner = TestRunner(**parser.parse_args(sys.argv[1:]).__dict__)
    failures = test_runner.run_tests(['tests'])
    sys.exit(bool(failures))
