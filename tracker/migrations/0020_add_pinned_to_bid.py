# Generated by Django 2.2.16 on 2021-01-04 03:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0019_add_pinned_to_donation'),
    ]

    operations = [
        migrations.AddField(
            model_name='bid',
            name='pinned',
            field=models.BooleanField(default=False, help_text='Will always show up in the current feeds'),
        ),
    ]
