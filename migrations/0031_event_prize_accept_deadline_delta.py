# -*- coding: utf-8 -*-


from django.db import migrations, models
import tracker.validators


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0030_add_prize_country_filters"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="prize_accept_deadline_delta",
            field=models.IntegerField(
                default=14,
                help_text="The number of days a winner will be given to accept a prize before it is re-rolled.",
                verbose_name="Prize Accept Deadline Delta",
                validators=[tracker.validators.positive, tracker.validators.nonzero],
            ),
        ),
    ]
