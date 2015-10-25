# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0007_remove_donor_runner_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='submission',
            name='console',
            field=models.TextField(default='', max_length=32),
            preserve_default=False,
        ),
    ]
