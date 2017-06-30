# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import tracker.validators


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0036_tech_notes_permissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='donation',
            name='requestedsolicitemail',
            field=models.CharField(default=b'CURR', max_length=32, verbose_name=b'Requested Charity Email Opt In', choices=[(b'CURR', b'Use Existing (Opt Out if not set)'), (b'OPTOUT', b'Opt Out'), (b'OPTIN', b'Opt In')]),
        ),
        migrations.AddField(
            model_name='donor',
            name='solicitemail',
            field=models.CharField(default=b'CURR', max_length=32, choices=[(b'CURR', b'Use Existing (Opt Out if not set)'), (b'OPTOUT', b'Opt Out'), (b'OPTIN', b'Opt In')]),
        ),
    ]
