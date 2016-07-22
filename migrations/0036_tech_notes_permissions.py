# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0035_merge'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='speedrun',
            options={'ordering': ['event__date', 'order'], 'verbose_name': 'Speed Run', 'permissions': (('can_view_tech_notes', 'Can view tech notes'),)},
        ),
        migrations.AlterField(
            model_name='speedrun',
            name='coop',
            field=models.BooleanField(default=False, help_text=b'Cooperative runs should be marked with this for layout purposes'),
        ),
    ]
