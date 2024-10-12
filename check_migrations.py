#!/usr/bin/env python
import os

import django

if __name__ == '__main__':
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_settings'
    # TODO: need to move tracker into a subfolder so this isn't necessary
    django.setup()

    from django.core import management

    management.call_command('migrate')
    management.call_command('makemigrations', 'tracker', check=True, dry_run=True)
