# -*- coding: utf-8 -*-


from django.db import migrations, models
import tracker.validators


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0036_tech_notes_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="donation",
            name="requestedsolicitemail",
            field=models.CharField(
                default="CURR",
                max_length=32,
                verbose_name="Requested Charity Email Opt In",
                choices=[
                    ("CURR", "Use Existing (Opt Out if not set)"),
                    ("OPTOUT", "Opt Out"),
                    ("OPTIN", "Opt In"),
                ],
            ),
        ),
        migrations.AddField(
            model_name="donor",
            name="solicitemail",
            field=models.CharField(
                default="CURR",
                max_length=32,
                choices=[
                    ("CURR", "Use Existing (Opt Out if not set)"),
                    ("OPTOUT", "Opt Out"),
                    ("OPTIN", "Opt In"),
                ],
            ),
        ),
    ]
