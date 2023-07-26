# Generated by Django 3.2.20 on 2023-07-26 10:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0030_add_bid_chain'),
    ]

    operations = [
        migrations.AlterField(
            model_name='donation',
            name='currency',
            field=models.CharField(choices=[('USD', 'US Dollars'), ('CAD', 'Canadian Dollars'), ('EUR', 'Euros')], max_length=8, verbose_name='Currency'),
        ),
        migrations.AlterField(
            model_name='event',
            name='paypalcurrency',
            field=models.CharField(choices=[('USD', 'US Dollars'), ('CAD', 'Canadian Dollars'), ('EUR', 'Euros')], default='USD', max_length=8, verbose_name='Currency'),
        ),
    ]
