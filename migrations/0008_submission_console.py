# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0007_remove_donor_runner_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="console",
            field=models.TextField(default="", max_length=32),
            preserve_default=False,
        ),
    ]
