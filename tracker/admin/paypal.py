from django.contrib.admin import register

from tracker import models
from .util import CustomModelAdmin


@register(models.IPNSettings)
class IPNSettingsAdmin(CustomModelAdmin):
    list_display = ('event', 'receiver_email')


@register(models.DonorPayPalInfo)
class DonorPayPalInfoAdmin(CustomModelAdmin):
    search_fields = (
        'donor__email',
        'donor__first_name',
        'donor__last_name',
        'payer_id',
        'payer_email',
    )
    list_display = ('donor', 'payer_id', 'payer_email', 'payer_verified')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
