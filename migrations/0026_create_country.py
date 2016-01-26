# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.management
import django.core.validators

import tracker.util as util


def add_countries(apps, schema_editor):
    django.core.management.call_command('loaddata', 'countries')


def migrate_to_country_code(apps, schema_editor):
    Country = apps.get_model('tracker', 'Country')
    Donor = apps.get_model('tracker', 'Donor')
    PayPalIPN = apps.get_model('ipn', 'PayPalIPN')
    for d in Donor.objects.all():
        if d.addresscountry:
            foundCountry = Country.objects.filter(name=d.addresscountry)
            if not foundCountry.exists():
                foundCountry = Country.objects.filter(alpha2=d.addresscountry)
            if not foundCountry.exists():
                foundCountry = Country.objects.filter(alpha3=d.addresscountry)
            if not foundCountry.exists():
                if util.try_parse_int(d.addresscountry) != None:
                    foundCountry = Country.objects.filter(numeric=d.addresscountry)
            # As a last resort, search through this user's most recent IPN for country data
            if not foundCountry.exists() and d.paypalemail:
                foundIPNs = PayPalIPN.objects.filter(payer_email=d.email).order_by('-payment_date')
                if foundIPNs.exists():
                    foundIPN = foundIPNs[0]
                    foundCountry = Country.objects.filter(alpha2=foundIPN.address_country_code)
            if foundCountry.exists():
                d.migrateaddresscountry = foundCountry[0]
                d.save()
        
def migrate_from_country_code(apps, schema_editor):
    Donor = apps.get_model('tracker', 'Donor')
    for d in Donor.objects.all():
        if d.migrateaddresscountry:
            d.addresscountry = d.migrateaddresscountry.alpha2
            d.save()

class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0025_event_minimumdonation'),
        # oddly enough, since the IPN model is migrated separately, we need to
        # reference the app as 'ipn' instead of 'paypal'
        ('ipn', '__latest__'),
    ]

    operations = [
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'Official ISO 3166 name for the country', unique=True, max_length=64)),
                ('alpha2', models.CharField(help_text=b'ISO 3166-1 Two-letter code', unique=True, max_length=2, validators=[django.core.validators.RegexValidator(regex=b'^[A-Z]{2}$', message=b'Country Alpha-2 code must be exactly 2 uppercase alphabetic characters')])),
                ('alpha3', models.CharField(help_text=b'ISO 3166-1 Three-letter code', unique=True, max_length=3, validators=[django.core.validators.RegexValidator(regex=b'^[A-Z]{3}$', message=b'Country Alpha-3 code must be exactly 3 uppercase alphabetic characters')])),
                ('numeric', models.CharField(help_text=b'ISO 3166-1 numeric code', blank=True, null=True, unique=True, max_length=3, validators=[django.core.validators.RegexValidator(regex=b'^\\\\d{3}$', message=b'Country Numeric code must be exactly 3 digits')])),
            ],
            options={
                'ordering': ('alpha2',),
                'permissions': (('can_edit_countries', 'Can edit countries'),),
            },
        ),
        migrations.RunPython(add_countries, lambda a,s: None),
        migrations.AddField(
            model_name='donor',
            name='migrateaddresscountry',
            field=models.ForeignKey(null=True,blank=True,default=None,verbose_name='Country', to='tracker.Country'),
        ),
        migrations.RunPython(migrate_to_country_code, migrate_from_country_code ),
        migrations.RemoveField(
            model_name='donor',
            name='addresscountry',
        ),
        migrations.RenameField(
            model_name='donor',
            old_name='migrateaddresscountry',
            new_name='addresscountry',
        ),
    ]
