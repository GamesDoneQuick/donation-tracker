# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0029_event_disallowed_prize_regions'),
    ]

    operations = [
        migrations.AddField(
            model_name='prize',
            name='allowed_prize_countries',
            field=models.ManyToManyField(help_text=b'List of countries whose residents are allowed to receive prizes (leave blank to allow all countries)', to='tracker.Country', verbose_name=b'Prize Countries', blank=True),
        ),
        migrations.AddField(
            model_name='prize',
            name='custom_country_filter',
            field=models.BooleanField(default=False, help_text=b'If checked, use a different country filter than that of the event.', verbose_name=b'Use Custom Country Filter'),
        ),
        migrations.AddField(
            model_name='prize',
            name='disallowed_prize_regions',
            field=models.ManyToManyField(help_text=b'A blacklist of regions within allowed countries that are not allowed for drawings (e.g. Quebec in Canada)', to='tracker.CountryRegion', verbose_name=b'Disallowed Regions', blank=True),
        ),
    ]
