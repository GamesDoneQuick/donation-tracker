# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0019_event_prize_email_templates"),
    ]

    operations = [
        migrations.AddField(
            model_name="prize",
            name="reviewnotes",
            field=models.TextField(
                help_text="Notes for the contributor (for example, why a particular prize was denied)",
                max_length=1024,
                verbose_name="Review Notes",
                blank=True,
            ),
        ),
    ]
