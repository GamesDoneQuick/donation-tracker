# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0011_add_speedrun_category_releaseyear'),
    ]

    operations = [
        migrations.AddField(
            model_name='speedrun',
            name='giantbomb_id',
            field=models.IntegerField(help_text=b'Identifies the game in the GiantBomb database, to allow auto-population of game data.', null=True, verbose_name=b'GiantBomb Database ID', blank=True),
        ),
    ]
