from django.contrib.admin import register

from tracker import models
from .forms import CountryRegionForm
from .util import CustomModelAdmin


@register(models.CountryRegion)
class CountryRegionAdmin(CustomModelAdmin):
    form = CountryRegionForm
    list_display = (
        'name',
        'country',
    )
    list_display_links = ('country',)
    search_fields = (
        'name',
        'country__name',
    )
    list_filter = ('country',)
    fieldsets = [
        (
            None,
            {
                'fields': ['name', 'country'],
            },
        ),
    ]
