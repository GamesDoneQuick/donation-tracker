# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
import tracker.models.event

def fill_in_order_column(apps, schema_editor):
    SpeedRun = apps.get_model('tracker', 'SpeedRun')
    for run in SpeedRun.objects.filter(order=None).order_by('starttime'):
        prev = SpeedRun.objects.filter(event=run.event).exclude(order=None).order_by('starttime').last()
        prev_order = (prev and prev.order) or 0
        run.order = prev_order + 1
        run.save()

def clear_order_column(apps, schema_editor):
    SpeedRun = apps.get_model('tracker', 'SpeedRun')
    SpeedRun.objects.update(order=None)

class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0005_run_commentators'),
    ]

    operations = [
        migrations.AddField(
            model_name='speedrun',
            name='console',
            field=models.CharField(max_length=32, blank=True),
        ),
        migrations.AlterField(
            model_name='speedrun',
            name='deprecated_runners',
            field=models.CharField(blank=True, verbose_name=b'*DEPRECATED* Runners', max_length=1024, editable=False, validators=[tracker.models.event.runners_exists]),
        ),
        migrations.AlterField(
            model_name='speedrun',
            name='name',
            field=models.CharField(max_length=64),
        ),
        migrations.RunPython(
            fill_in_order_column,
            clear_order_column,
        )
    ]
