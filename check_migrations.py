#!/usr/bin/env python
import os

import django

if __name__ == '__main__':
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_settings'
    # TODO: need to move tracker into a subfolder so this isn't necessary
    django.setup()

    from django.core import management
    from django.core.management.commands import migrate
    from django.core.management.commands import makemigrations

    management.call_command(migrate.Command())
    management.call_command(makemigrations.Command(), check=True, dry_run=True)
