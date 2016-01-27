# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0032_prizewinner_auth_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='prizewinner',
            name='shipping_receipt_url',
            field=models.URLField(help_text=b'The URL of an image of the shipping receipt', max_length=1024, verbose_name=b'Shipping Receipt Image URL', blank=True),
        ),
    ]
