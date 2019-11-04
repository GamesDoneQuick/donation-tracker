# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0014_donor_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="prize",
            name="requiresshipping",
            field=models.BooleanField(
                default=True, verbose_name="Requires Postal Shipping"
            ),
        ),
        migrations.AddField(
            model_name="prizewinner",
            name="shippingnotes",
            field=models.TextField(
                max_length=2048, verbose_name="Shipping Notes", blank=True
            ),
        ),
        migrations.AddField(
            model_name="prizewinner",
            name="winnernotes",
            field=models.TextField(
                max_length=1024, verbose_name="Winner Notes", blank=True
            ),
        ),
    ]
