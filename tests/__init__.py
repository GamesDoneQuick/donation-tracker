import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tracker.tests.test_settings')
django.setup()
