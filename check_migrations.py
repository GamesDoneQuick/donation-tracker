#!/usr/bin/env python
import os
import sys

import django

if __name__ == '__main__':
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_settings'
    # TODO: need to move tracker into a subfolder so this isn't necessary
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    django.setup()

    from django.core import management
    from django.core.management.commands import migrate
    from django.core.management.commands import makemigrations

    management.call_command(migrate.Command())
    management.call_command(makemigrations.Command(), check=True, dry_run=True)
