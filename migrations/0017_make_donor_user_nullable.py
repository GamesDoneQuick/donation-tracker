# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import tracker.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0016_prizewinner_acceptemailsentcount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='donor',
            name='user',
            field=tracker.models.fields.OneToOneOrNoneField(null=True, blank=True, to=settings.AUTH_USER_MODEL),
        ),
    ]
