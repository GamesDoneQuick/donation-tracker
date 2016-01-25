# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0027_event_prize_countries'),
    ]

    operations = [
        migrations.CreateModel(
            name='CountryRegion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=128)),
            ],
            options={
                'ordering': ('country', 'name'),
                'verbose_name': 'country region',
            },
        ),
        migrations.AlterModelOptions(
            name='country',
            options={'ordering': ('alpha2',), 'verbose_name_plural': 'countries'},
        ),
        migrations.AddField(
            model_name='countryregion',
            name='country',
            field=models.ForeignKey(to='tracker.Country', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AlterUniqueTogether(
            name='countryregion',
            unique_together=set([('name', 'country')]),
        ),
    ]
