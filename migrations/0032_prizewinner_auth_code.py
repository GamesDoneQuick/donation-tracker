# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import tracker.util


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0031_event_prize_accept_deadline_delta'),
    ]

    operations = [
        migrations.AddField(
            model_name='prizewinner',
            name='auth_code',
            field=models.CharField(default=tracker.util.make_auth_code, help_text=b'Used instead of a login for winners to manage prizes.', max_length=64, editable=False),
        ),
    ]
