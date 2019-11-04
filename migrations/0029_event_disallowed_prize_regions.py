# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0028_add_country_region"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="disallowed_prize_regions",
            field=models.ManyToManyField(
                help_text="A blacklist of regions within allowed countries that are not allowed for drawings (e.g. Quebec in Canada)",
                to="tracker.CountryRegion",
                verbose_name="Disallowed Regions",
                blank=True,
            ),
        ),
    ]
