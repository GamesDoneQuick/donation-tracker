# Generated by Django 5.1.4 on 2025-01-21 01:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ipn', '0008_auto_20181128_1032'),
        ('tracker', '0054_delete_event_targetamount'),
    ]

    operations = [
        migrations.AddField(
            model_name='donation',
            name='ipns',
            field=models.ManyToManyField(blank=True, to='ipn.paypalipn', related_name='donation'),
        ),
        migrations.AddField(
            model_name='donation',
            name='cleared_at',
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
    ]
