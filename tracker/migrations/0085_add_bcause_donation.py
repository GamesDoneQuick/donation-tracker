from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0084_merge_20260618_2116'),
    ]

    operations = [
        migrations.CreateModel(
            name='BcauseDonation',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('amount_cents', models.IntegerField()),
                ('beneficiary_id', models.CharField(max_length=64)),
                ('currency_code', models.CharField(max_length=8)),
                ('date_valuta_utc', models.DateTimeField()),
                ('donor_name', models.CharField(blank=True, max_length=64, null=True)),
                ('email', models.EmailField(blank=True, max_length=64, null=True)),
                ('fee_cents', models.IntegerField(default=0)),
                ('metadata', models.JSONField(blank=True)),
                ('sandbox', models.BooleanField()),
                ('status', models.CharField(max_length=64)),
                ('transaction_id', models.CharField(max_length=64, unique=True)),
                ('user_id', models.CharField(blank=True, max_length=64, null=True)),
            ],
        ),
    ]
