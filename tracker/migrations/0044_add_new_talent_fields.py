# Generated by Django 5.1 on 2024-09-30 20:14

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0043_add_model_tags'),
    ]

    operations = [
        migrations.AddField(
            model_name='speedrun',
            name='thosts',
            field=models.ManyToManyField(blank=True, related_name='thosting', to='tracker.runner'),
        ),
        migrations.AddField(
            model_name='speedrun',
            name='tcommentators',
            field=models.ManyToManyField(blank=True, related_name='tcommentating_for', to='tracker.runner'),
        ),
    ]