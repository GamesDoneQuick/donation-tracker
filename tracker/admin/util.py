from ajax_select.admin import AjaxSelectAdmin
from django.core.exceptions import PermissionDenied
from django.urls import reverse


def reverse_lazy(url):
    return lambda: reverse(url)


def latest_event_id():
    from tracker.models import Event

    try:
        return Event.objects.latest().id
    except Event.DoesNotExist:
        return 0


class CustomModelAdmin(AjaxSelectAdmin):
    pass


def ReadOffsetTokenPair(value):
    toks = value.split('-')
    feed = toks[0]
    params = {}
    if len(toks) > 1:
        params['delta'] = toks[1]
    return feed, params


def mass_assign_action(self, request, queryset, field, value):
    queryset.update(**{field: value})
    self.message_user(request, 'Updated %s to %s' % (field, value))


def api_urls():
    return {
        'adminBaseURL': reverse('admin:app_list', kwargs={'app_label': 'tracker'}),
        'searchURL': reverse('tracker:api_v1:search'),
        'editURL': reverse('tracker:api_v1:edit'),
        'addURL': reverse('tracker:api_v1:add'),
        'deleteURL': reverse('tracker:api_v1:delete'),
    }


class EventLockedMixin:
    def _has_locked_permission(self, request, obj):
        event = self.get_event(obj)
        return (
            obj is None
            or not (event and event.locked)
            or (
                request.user and request.user.has_perm('tracker.can_edit_locked_events')
            )
        )

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(
            request, obj
        ) and self._has_locked_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(
            request, obj
        ) and self._has_locked_permission(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # this prevents the event field, if any, from showing locked events as a choice

        if not request.user.has_perm('tracker.can_edit_locked_events'):
            queryset = getattr(form.base_fields.get('event', None), 'queryset', None)
            if queryset:
                form.base_fields['event'].queryset = queryset.filter(locked=False)
            for field in self.get_event_child_fields():
                queryset = getattr(form.base_fields.get(field, None), 'queryset', None)
                if queryset:
                    form.base_fields[field].queryset = queryset.filter(
                        event__locked=False
                    )
        return form

    def save_form(self, request, form, change):
        if not request.user.has_perm('tracker.can_edit_locked_events'):
            event = form.cleaned_data.get('event', None)
            # this is a truly degenerate case
            # a user either has to be:
            # - adding a new child to event N
            # - changing an existing child to point to event N when it wasn't before
            # in addition to the following two conditions:
            # - event N was not locked when the user opened the form, but got locked before the user could save
            # - was not caught by existing machinery (choice validation, etc)
            if event.locked:
                raise PermissionDenied
            for field in self.get_event_child_fields():
                model = form.cleaned_data.get('field', None)
                if model and model.event.locked:
                    raise PermissionDenied
        return super().save_form(request, form, change)

    def get_event(self, obj):
        return obj and obj.event

    def get_event_child_fields(self):
        return getattr(self, 'event_child_fields', [])


class DonationStatusMixin:
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not request.user.has_perm('tracker.view_pending_donation'):
            queryset = queryset.filter(donation__transactionstate='COMPLETED')
        if not request.user.has_perm('tracker.view_test'):
            queryset = queryset.filter(donation__testdonation=False)
        return queryset

    def get_list_display(self, request):
        list_display = list(super().get_list_display(request))
        if not request.user.has_perm('tracker.view_pending_donation'):
            list_display.remove('transactionstate')
        if not request.user.has_perm('tracker.view_test'):
            list_display.remove('testdonation')
        return list_display

    def get_list_filter(self, request):
        list_filter = list(super().get_list_filter(request))
        if not request.user.has_perm('tracker.view_pending_donation'):
            list_filter.remove('donation__transactionstate')
        if not request.user.has_perm('tracker.view_pending_donation'):
            list_filter.remove('donation__testdonation')
        return list_filter
