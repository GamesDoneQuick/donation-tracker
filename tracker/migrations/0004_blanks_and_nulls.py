# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
import tracker.models.event


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0003_add_event_timezone'),
    ]

    operations = [
        migrations.AlterField(
            model_name='runner',
            name='stream',
            field=models.URLField(max_length=128, blank=True),
        ),
        migrations.AlterField(
            model_name='runner',
            name='twitter',
            field=models.SlugField(max_length=15, blank=True),
        ),
        migrations.AlterField(
            model_name='runner',
            name='youtube',
            field=models.SlugField(max_length=20, blank=True),
        ),
        migrations.AlterField(
            model_name='speedrun',
            name='endtime',
            field=models.DateTimeField(verbose_name=b'End Time', null=True, editable=False),
        ),
        migrations.AlterField(
            model_name='speedrun',
            name='starttime',
            field=models.DateTimeField(verbose_name=b'Start Time', null=True, editable=False),
        ),
    ]
