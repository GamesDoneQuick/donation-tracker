# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0010_one_to_one_and_typo_fix'),
    ]

    operations = [
        migrations.AddField(
            model_name='speedrun',
            name='category',
            field=models.TextField(help_text=b'The type of run being performed', max_length=32, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='speedrun',
            name='release_year',
            field=models.IntegerField(help_text=b'The year the game was released', null=True, verbose_name=b'Release Year', blank=True),
        ),
        migrations.AlterUniqueTogether(
            name='speedrun',
            unique_together=set([('event', 'order'), ('name', 'category', 'event')]),
        ),
    ]
