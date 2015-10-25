# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0009_change_flowmodel_credentialsmodel_to_1to1_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bid',
            name='biddependency',
            field=models.ForeignKey(related_name='dependent_bids', on_delete=django.db.models.deletion.PROTECT, verbose_name=b'Dependency', blank=True, to='tracker.Bid', null=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='user',
            field=models.OneToOneField(to=settings.AUTH_USER_MODEL),
        ),
    ]
