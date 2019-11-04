# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-12-21 04:08


from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("tracker", "0006_alter_runners"),
    ]

    operations = [
        migrations.CreateModel(
            name="PrizeKey",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("key", models.CharField(max_length=64, unique=True)),
            ],
            options={"ordering": ["prize"], "verbose_name": "Prize Key"},
        ),
        migrations.AddField(
            model_name="prize",
            name="key_code",
            field=models.BooleanField(
                default=False,
                help_text="If true, this prize is a key code of some kind rather than a physical prize. Disables multiwin and locks max winners to the number of keys available.",
            ),
        ),
        migrations.AddField(
            model_name="prizekey",
            name="prize",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, to="tracker.Prize"
            ),
        ),
        migrations.AddField(
            model_name="prizekey",
            name="prize_winner",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="tracker.PrizeWinner",
            ),
        ),
        migrations.AlterModelOptions(
            name="prizekey",
            options={
                "ordering": ["prize"],
                "permissions": (
                    ("edit_prize_key_keys", "Can edit existing prize keys"),
                    ("remove_prize_key_winners", "Can remove winners from prize keys"),
                ),
                "verbose_name": "Prize Key",
            },
        ),
    ]
