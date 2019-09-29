# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0017_make_donor_user_nullable'),
    ]

    operations = [
        migrations.AddField(
            model_name='prizewinner',
            name='couriername',
            field=models.CharField(help_text='e.g. FedEx, DHL, ...', max_length=64, verbose_name='Courier Service Name', blank=True),
        ),
    ]
