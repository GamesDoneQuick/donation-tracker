# -*- coding: utf-8 -*-


from django.db import migrations, models


def copy_over_display_name(apps, schema_editor):
    SpeedRun = apps.get_model('tracker', 'SpeedRun')
    for run in SpeedRun.objects.all():
        run.display_name = run.name
        run.save()


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0022_textfields_to_charfields'),
    ]

    operations = [
        migrations.AddField(
            model_name='speedrun',
            name='display_name',
            field=models.TextField(help_text='How to display this game on the stream.', max_length=256, verbose_name='Display Name', blank=True),
        ),
        migrations.RunPython(copy_over_display_name),
    ]
