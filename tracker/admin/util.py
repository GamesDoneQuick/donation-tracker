from ajax_select.admin import AjaxSelectAdmin
from django.urls import reverse


def reverse_lazy(url):
    return lambda: reverse(url)


def latest_event_id():
    from tracker.models import Event

    try:
        return Event.objects.latest().id
    except Event.DoesNotExist:
        return 0


def current_event_id():
    from tracker.models import Event

    current = Event.objects.current()

    return current.id if current else 0


def current_or_next_event_id():
    from tracker.models import Event

    current = Event.objects.current() or Event.objects.next()

    return current.id if current else 0


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
