# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0036_tech_notes_permissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='steam_id',
            field=models.BigIntegerField(null=True, verbose_name=b'SteamID', blank=True),
        ),
    ]
