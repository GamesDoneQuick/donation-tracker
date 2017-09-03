# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
import tracker.validators


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0037_add_email_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='donation',
            name='bidstate',
            field=models.CharField(default=b'PENDING', max_length=255, verbose_name=b'Bid State', db_index=True, choices=[(b'PENDING', b'Pending'), (b'IGNORED', b'Ignored'), (b'PROCESSED', b'Processed'), (b'FLAGGED', b'Flagged')]),
        ),
        migrations.AlterField(
            model_name='donation',
            name='commentstate',
            field=models.CharField(default=b'ABSENT', max_length=255, verbose_name=b'Comment State', db_index=True, choices=[(b'ABSENT', b'Absent'), (b'PENDING', b'Pending'), (b'DENIED', b'Denied'), (b'APPROVED', b'Approved'), (b'FLAGGED', b'Flagged')]),
        ),
        migrations.AlterField(
            model_name='donation',
            name='readstate',
            field=models.CharField(default=b'PENDING', max_length=255, verbose_name=b'Read State', db_index=True, choices=[(b'PENDING', b'Pending'), (b'READY', b'Ready to Read'), (b'IGNORED', b'Ignored'), (b'READ', b'Read'), (b'FLAGGED', b'Flagged')]),
        ),
        migrations.AlterField(
            model_name='donation',
            name='transactionstate',
            field=models.CharField(default=b'PENDING', max_length=64, verbose_name=b'Transaction State', db_index=True, choices=[(b'PENDING', b'Pending'), (b'COMPLETED', b'Completed'), (b'CANCELLED', b'Cancelled'), (b'FLAGGED', b'Flagged')]),
        ),
        migrations.AlterField(
            model_name='donation',
            name='timereceived',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name=b'Time Received', db_index=True),
        ),
    ]
