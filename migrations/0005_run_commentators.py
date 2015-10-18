# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
import tracker.models.event


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0004_blanks_and_nulls'),
    ]

    operations = [
        migrations.AddField(
            model_name='speedrun',
            name='commentators',
            field=models.CharField(max_length=1024, blank=True),
        ),
    ]
