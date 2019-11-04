# -*- coding: utf-8 -*-


from django.db import migrations
import timezone_field.fields


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0002_add_external_submissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="timezone",
            field=timezone_field.fields.TimeZoneField(default="US/Eastern"),
        ),
    ]
