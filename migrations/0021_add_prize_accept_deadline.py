# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0020_prize_reviewnotes'),
    ]

    operations = [
        migrations.AddField(
            model_name='prizewinner',
            name='acceptdeadline',
            field=models.DateTimeField(default=None, help_text=b'The deadline for this winner to accept their prize (leave blank for no deadline)', null=True, verbose_name=b'Winner Accept Deadline', blank=True),
        ),
    ]
