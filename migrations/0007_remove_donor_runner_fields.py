# -*- coding: utf-8 -*-


from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0006_run_console_and_fill_in_order'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='donor',
            name='runnertwitch',
        ),
        migrations.RemoveField(
            model_name='donor',
            name='runnertwitter',
        ),
        migrations.RemoveField(
            model_name='donor',
            name='runneryoutube',
        ),
    ]
