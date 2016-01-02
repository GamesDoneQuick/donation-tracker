# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings

def write_existing_providers(apps, schema_editor):
    Prize = apps.get_model('tracker', 'Prize')
    for prize in Prize.objects.all():
        if prize.handler:
            if prize.handler.username != prize.handler.email:
                prize.provider = prize.handler.username
            prize.save()


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0023_add_display_name'),
    ]

    operations = [
        migrations.RenameField('prize', 'provider', 'handler'),
        migrations.AddField(
            model_name='prize',
            name='provider',
            field=models.CharField(max_length=64, blank=True),
        ),
        migrations.AlterField(
            model_name='prize',
            name='handler',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, help_text=b'User account responsible for prize shipping', null=True),
        ),
        migrations.AlterField(
            model_name='prize',
            name='provider',
            field=models.CharField(help_text=b'Name of the person who provided the prize to the event', max_length=64, blank=True),
        ),
        migrations.RunPython(write_existing_providers),
    ]
