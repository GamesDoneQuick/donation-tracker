from django.db import models
from django.core.validators import RegexValidator

def exactly_length(l):
    def _closure(s):
        return len(s) == l
    return _closure

class CountryManager(models.Manager):
    def get_by_natural_key(self, alpha2):
        return self.get(short=alpha2)

class Country(models.Model):
    objects = CountryManager()
    
    name = models.CharField(max_length=64, null=False, blank=False, unique=True, help_text='Official ISO 3166 name for the country')
    alpha2 = models.CharField(max_length=2, null=False, blank=False, unique=True, validators=[RegexValidator(regex=r'^[A-Z]{2}$', message='Country Alpha-2 code must be exactly 2 uppercase alphabetic characters')], help_text='ISO 3166-1 Two-letter code')
    alpha3 = models.CharField(max_length=3, null=False, blank=False, unique=True, validators=[RegexValidator(regex=r'^[A-Z]{3}$', message='Country Alpha-3 code must be exactly 3 uppercase alphabetic characters')], help_text='ISO 3166-1 Three-letter code')
    numeric = models.CharField(max_length=3, null=True, blank=True, unique=True, validators=[RegexValidator(regex=r'^\\d{3}$', message='Country Numeric code must be exactly 3 digits')], help_text='ISO 3166-1 numeric code') # allowing this to be null to allow for non-countries such as paypal's fake China

    def __unicode__(self):
        return self.name
        
    def natural_key(self):
        return self.alpha2
    
    class Meta:
        app_label = 'tracker'
        permissions = (
            ('can_edit_countries', 'Can edit countries'),
        )
        ordering = ('alpha2',)
        