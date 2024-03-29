# Generated by Django 4.2 on 2023-05-13 21:11

from decimal import Decimal
from django.db import migrations, models
import tracker.validators


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0031_add_donor_cache_indices'),
    ]

    operations = [
        migrations.AlterField(
            model_name='donation',
            name='amount',
            field=models.DecimalField(db_index=True, decimal_places=2, default=Decimal('0.00'), max_digits=20, validators=[tracker.validators.positive, tracker.validators.nonzero], verbose_name='Donation Amount'),
        ),
        migrations.AlterField(
            model_name='donor',
            name='visibility',
            field=models.CharField(choices=[('FULL', 'Fully Visible'), ('FIRST', 'First Name, Last Initial'), ('ALIAS', 'Alias Only'), ('ANON', 'Anonymous')], db_index=True, default='FIRST', max_length=32),
        ),
    ]
