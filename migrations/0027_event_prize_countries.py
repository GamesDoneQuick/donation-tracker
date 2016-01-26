# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0026_create_country'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='allowed_prize_countries',
            field=models.ManyToManyField(help_text=b'List of countries whose residents are allowed to receive prizes (leave blank to allow all countries)', to='tracker.Country', verbose_name=b'Allowed Prize Countries', blank=True),
        ),
    ]
