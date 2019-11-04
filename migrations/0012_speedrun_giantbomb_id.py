# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0011_add_speedrun_category_releaseyear"),
    ]

    operations = [
        migrations.AddField(
            model_name="speedrun",
            name="giantbomb_id",
            field=models.IntegerField(
                help_text="Identifies the game in the GiantBomb database, to allow auto-population of game data.",
                null=True,
                verbose_name="GiantBomb Database ID",
                blank=True,
            ),
        ),
    ]
