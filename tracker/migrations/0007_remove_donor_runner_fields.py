# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
import tracker.models.event


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0006_run_console_and_fill_in_order'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='donor',
            name='runnertwitch',
        ),
        migrations.RemoveField(
            model_name='donor',
            name='runnertwitter',
        ),
        migrations.RemoveField(
            model_name='donor',
            name='runneryoutube',
        ),
    ]
