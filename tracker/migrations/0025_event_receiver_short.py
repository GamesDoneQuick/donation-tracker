# Generated by Django 4.1.5 on 2023-03-18 22:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0024_add_challenge_repeat'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='receiver_short',
            field=models.CharField(blank=True, help_text='Useful for space constrained displays', max_length=16, verbose_name='Receiver Name (Short)'),
        ),
    ]
