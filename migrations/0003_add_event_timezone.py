# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
import timezone_field.fields
import tracker.models.event


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0002_add_external_submissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='timezone',
            field=timezone_field.fields.TimeZoneField(default=b'US/Eastern'),
        ),
    ]
