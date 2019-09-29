# -*- coding: utf-8 -*-


from django.db import migrations, models
from decimal import Decimal
import tracker.validators


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0024_prize_handler'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='minimumdonation',
            field=models.DecimalField(decimal_places=2, default=Decimal('1.00'), max_digits=20, validators=[tracker.validators.positive, tracker.validators.nonzero], help_text='Enforces a minimum donation amount on the donate page.', verbose_name='Minimum Donation'),
        ),
    ]
