# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0004_blanks_and_nulls'),
    ]

    operations = [
        migrations.AddField(
            model_name='speedrun',
            name='commentators',
            field=models.CharField(max_length=1024, blank=True),
        ),
    ]
