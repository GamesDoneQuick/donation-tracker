# -*- coding: utf-8 -*-


from django.db import migrations, models
import tracker.validators


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0015_add_prizewinner_notes_prize_requiresshipping'),
    ]

    operations = [
        migrations.AddField(
            model_name='prizewinner',
            name='acceptemailsentcount',
            field=models.IntegerField(default=0, help_text='The number of accepts that the previous e-mail was sent for (or 0 if none were sent yet).', verbose_name='Accept Count Sent For', validators=[tracker.validators.positive]),
        ),
    ]
