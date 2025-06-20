from django.contrib import admin
from django.contrib.admin import models as admin_models
from django.contrib.admin import register
from django.core.exceptions import ObjectDoesNotExist
from django.utils.html import format_html

from tracker import models

from .filters import AdminActionLogEntryFlagFilter
from .util import CustomModelAdmin


@register(models.Log)
class LogAdmin(CustomModelAdmin):
    search_fields = ['category', 'message']
    date_hierarchy = 'timestamp'
    list_filter = [('timestamp', admin.DateFieldListFilter), 'event', 'user']
    fieldsets = [
        (
            None,
            {
                'fields': [
                    'timestamp',
                    'category',
                    'event',
                    'user',
                    'message',
                ]
            },
        ),
    ]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('event')

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@register(admin_models.LogEntry)
class AdminActionLogEntryAdmin(CustomModelAdmin):
    search_fields = ['object_repr', 'change_message']
    date_hierarchy = 'action_time'
    list_filter = [
        ('action_time', admin.DateFieldListFilter),
        'user',
        'content_type',
        AdminActionLogEntryFlagFilter,
    ]
    list_display = ('edited_object', 'action_type', 'change_message_')
    fieldsets = [
        (
            None,
            {
                'fields': [
                    'action_type',
                    'action_time',
                    'user',
                    'change_message',
                    'target_object',
                    'content_type',
                    'content_type_id',
                    'object_id',
                ]
            },
        )
    ]

    def edited_object(self, obj):
        # FIXME: this is horribly inefficient, but browsing this casually probably shouldn't be happening either
        try:
            return obj.get_edited_object() or obj.object_repr
        except (AttributeError, ObjectDoesNotExist):
            # AttributeError can happen if the entry points at a model that is no longer installed
            return obj.object_repr

    def change_message_(self, obj):
        if obj.is_change():
            return obj.get_change_message()
        else:
            return '-'

    def action_type(self, instance):
        if instance.is_addition():
            return 'Addition'
        elif instance.is_change():
            return 'Change'
        elif instance.is_deletion():
            return 'Deletion'
        else:
            return 'Unknown'

    def target_object(self, instance):
        if instance.is_deletion():
            return '-'
        else:
            return format_html(
                '<a href="{admin_url}">{repr}</a>',
                admin_url=instance.get_admin_url(),
                repr=instance.object_repr,
            )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
