# -*- coding: utf-8 -*-


from django.db import migrations, models
import django.utils.timezone
import tracker.validators


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0037_add_email_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="donation",
            name="bidstate",
            field=models.CharField(
                default="PENDING",
                max_length=255,
                verbose_name="Bid State",
                db_index=True,
                choices=[
                    ("PENDING", "Pending"),
                    ("IGNORED", "Ignored"),
                    ("PROCESSED", "Processed"),
                    ("FLAGGED", "Flagged"),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="donation",
            name="commentstate",
            field=models.CharField(
                default="ABSENT",
                max_length=255,
                verbose_name="Comment State",
                db_index=True,
                choices=[
                    ("ABSENT", "Absent"),
                    ("PENDING", "Pending"),
                    ("DENIED", "Denied"),
                    ("APPROVED", "Approved"),
                    ("FLAGGED", "Flagged"),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="donation",
            name="readstate",
            field=models.CharField(
                default="PENDING",
                max_length=255,
                verbose_name="Read State",
                db_index=True,
                choices=[
                    ("PENDING", "Pending"),
                    ("READY", "Ready to Read"),
                    ("IGNORED", "Ignored"),
                    ("READ", "Read"),
                    ("FLAGGED", "Flagged"),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="donation",
            name="transactionstate",
            field=models.CharField(
                default="PENDING",
                max_length=64,
                verbose_name="Transaction State",
                db_index=True,
                choices=[
                    ("PENDING", "Pending"),
                    ("COMPLETED", "Completed"),
                    ("CANCELLED", "Cancelled"),
                    ("FLAGGED", "Flagged"),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="donation",
            name="timereceived",
            field=models.DateTimeField(
                default=django.utils.timezone.now,
                verbose_name="Time Received",
                db_index=True,
            ),
        ),
    ]
