# Generated by Django 2.2.16 on 2020-10-13 21:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0014_merge_20201008_2021'),
    ]

    operations = [
        migrations.AddField(
            model_name='donor',
            name='addressname',
            field=models.CharField(blank=True, max_length=128, verbose_name='Shipping Name'),
        ),
    ]
