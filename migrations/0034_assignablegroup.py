# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
        ('tracker', '0033_prizewinner_shipping_receipt_url'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssignableGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('group', models.OneToOneField(to='auth.Group')),
            ],
            options={
                'verbose_name': 'Assignable Group',
                'permissions': (('assign_allowed_group', 'Can assign allowed groups.'),),
            },
        ),
    ]
