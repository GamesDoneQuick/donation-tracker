# Generated by Django 2.2.16 on 2021-01-02 17:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0017_change_permission_names'),
    ]

    operations = [
        migrations.AddField(
            model_name='ad',
            name='blurb',
            field=models.TextField(blank=True, help_text='Text for hosts to read off'),
        ),
    ]