# Generated by Django 2.2.20 on 2021-12-21 05:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0024_event_receivernotice'),
    ]

    operations = [
        migrations.AddField(
            model_name='runner',
            name='nico',
            field=models.SlugField(blank=True, max_length=12, verbose_name='ニコニココミュニティID（co有）'),
        ),
        migrations.AddField(
            model_name='runner',
            name='twitch',
            field=models.SlugField(blank=True, max_length=25),
        ),
        migrations.AlterField(
            model_name='runner',
            name='platform',
            field=models.CharField(choices=[('TWITCH', 'Twitch'), ('MIXER', 'Mixer'), ('FACEBOOK', 'Facebook'), ('YOUTUBE', 'Youtube'), ('NICO', 'niconico')], default='TWITCH', help_text='Streaming Platforms', max_length=20),
        ),
    ]