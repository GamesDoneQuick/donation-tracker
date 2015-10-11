# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import django.db.models.deletion
import tracker.models.event


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Runner',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=64)),
                ('stream', models.URLField(max_length=128)),
                ('twitter', models.SlugField(max_length=15)),
                ('youtube', models.SlugField(max_length=20)),
                ('donor', models.OneToOneField(null=True, blank=True, to='tracker.Donor')),
            ],
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('external_id', models.IntegerField(serialize=False, primary_key=True)),
                ('game_name', models.TextField(max_length=64)),
                ('category', models.TextField(max_length=32)),
                ('estimate', tracker.models.event.TimestampField()),
            ],
        ),
        migrations.AlterModelOptions(
            name='speedrun',
            options={'ordering': ['event__date', 'order'], 'verbose_name': 'Speed Run'},
        ),
        migrations.AddField(
            model_name='speedrun',
            name='order',
            field=models.IntegerField(null=True, editable=False),
        ),
        migrations.AddField(
            model_name='speedrun',
            name='run_time',
            field=tracker.models.event.TimestampField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='speedrun',
            name='setup_time',
            field=tracker.models.event.TimestampField(default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='speedrun',
            name='deprecated_runners',
            field=models.CharField(verbose_name=b'*DEPRECATED* Runners', max_length=1024, editable=False, blank=True),
        ),
        migrations.AlterField(
            model_name='speedrun',
            name='endtime',
            field=models.DateTimeField(verbose_name=b'End Time', editable=False),
        ),
        migrations.AlterField(
            model_name='speedrun',
            name='runners',
            field=models.ManyToManyField(to='tracker.Runner'),
        ),
        migrations.AlterField(
            model_name='speedrun',
            name='starttime',
            field=models.DateTimeField(verbose_name=b'Start Time', editable=False),
        ),
        migrations.AlterUniqueTogether(
            name='speedrun',
            unique_together=set([('name', 'event'), ('event', 'order')]),
        ),
        migrations.AddField(
            model_name='submission',
            name='run',
            field=models.ForeignKey(to='tracker.SpeedRun'),
        ),
        migrations.AddField(
            model_name='submission',
            name='runner',
            field=models.ForeignKey(to='tracker.Runner'),
        ),
    ]
