# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0033_prizewinner_shipping_receipt_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='speedrun',
            name='coop',
            field=models.BooleanField(default=False),
        ),
    ]
