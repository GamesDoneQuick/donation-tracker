from django.contrib import admin
from django.contrib.admin import register, models as admin_models
from django.utils.safestring import mark_safe

from tracker import models
from .filters import AdminActionLogEntryFlagFilter
from .forms import LogAdminForm
from .util import CustomModelAdmin


@register(models.Log)
class LogAdmin(CustomModelAdmin):
    form = LogAdminForm
    search_fields = ['category', 'message']
    date_hierarchy = 'timestamp'
    list_filter = [('timestamp', admin.DateFieldListFilter), 'event', 'user']
    # logs are uneditable
    readonly_fields = [
        'timestamp',
        'category',
        'event',
        'user',
        'message',
    ]
    fieldsets = [
        (None, {'fields': ['timestamp', 'category', 'event', 'user', 'message',]}),
    ]

    def has_add_permission(self, request, obj=None):
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
        AdminActionLogEntryFlagFilter,
    ]
    readonly_fields = (
        'action_time',
        'content_type',
        'object_id',
        'object_repr',
        'action_type',
        'action_flag',
        'target_object',
        'change_message',
        'user',
    )
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
                ]
            },
        )
    ]

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
            return 'Deleted'
        else:
            return mark_safe(
                '<a href="{0}">{1}</a>'.format(
                    instance.get_admin_url(), instance.object_repr
                )
            )

    def has_add_permission(self, request, obj=None):
        return self.has_log_edit_perms(request, obj)

    def has_change_permission(self, request, obj=None):
        return self.has_log_edit_perms(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self.has_log_edit_perms(request, obj)

    def has_log_edit_perms(self, request, obj=None):
        return request.user.has_perm('tracker.can_change_log')
