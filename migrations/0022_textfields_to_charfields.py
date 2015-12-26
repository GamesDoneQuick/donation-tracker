# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0021_add_prize_accept_deadline'),
    ]

    operations = [
        migrations.AlterField(
            model_name='speedrun',
            name='category',
            field=models.CharField(help_text=b'The type of run being performed', max_length=64, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='submission',
            name='category',
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name='submission',
            name='console',
            field=models.CharField(max_length=32),
        ),
        migrations.AlterField(
            model_name='submission',
            name='game_name',
            field=models.CharField(max_length=64),
        ),
    ]
