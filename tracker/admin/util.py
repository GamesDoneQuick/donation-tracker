import contextlib
import re
import urllib.parse

import django
from django.apps import apps
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet
from django.forms import ModelForm
from django.http import Http404
from django.urls import resolve, reverse


def reverse_lazy(url):
    return lambda: reverse(url)


def current_event_id():
    from tracker.models import Event

    current = Event.objects.current()

    return current.id if current else 0


def current_or_next_event_id():
    from tracker.models import Event

    current = Event.objects.current() or Event.objects.next()

    return current.id if current else 0


class CustomModelAdmin(admin.ModelAdmin):
    def get_actions(self, request):
        actions = super().get_actions(request)
        if django.VERSION < (5, 1, 0):
            # TODO: remove when Django 4.2 is no longer supported
            actions.pop('delete_selected', None)
        return actions

    def get_parent_view(self, request):
        """
        tries to determine which view/object we're looking at based on the referer for autocomplete widgets
        """
        if (
            request.resolver_match is None
            or request.resolver_match.view_name != 'admin:autocomplete'
            or not request.META.get('HTTP_REFERER', None)
        ):
            return None
        with contextlib.suppress(Http404):
            match = resolve(
                urllib.parse.urlparse(request.META.get('HTTP_REFERER')).path
            )
            if not re.match(r'admin:tracker_\w+_(add|change)', match.view_name):
                return None
            model, action = match.url_name.split('_')[1:]
            return (
                model,
                action,
                match.kwargs['object_id'] if action == 'change' else None,
            )
        return None

    def get_parent_model(self, request):
        """
        tries to fetch the parent model based on the referer for autocomplete widgets
        """
        parent_view = self.get_parent_view(request)
        if parent_view and parent_view[1] == 'change':
            with contextlib.suppress(LookupError):
                return (
                    apps.get_model('tracker', parent_view[0])
                    .objects.filter(id=parent_view[2])
                    .first()
                )
        return None

    def has_view_permission(self, request, obj=None):
        return (
            request.resolver_match is not None
            and request.resolver_match.view_name == 'admin:autocomplete'
            and request.user.is_staff
        ) or super().has_view_permission(request, obj)


def ReadOffsetTokenPair(value):
    toks = value.split('-')
    feed = toks[0]
    params = {}
    if len(toks) > 1:
        params['delta'] = toks[1]
    return feed, params


def mass_assign_action(self, request, queryset, field, value):
    if not self.has_change_permission(request):
        raise PermissionDenied
    queryset.update(**{field: value})
    self.message_user(request, 'Updated %s to %s' % (field, value))


class EventArchivedMixin:
    def get_ordering(self, request):
        ordering = super().get_ordering(request) or self.opts.ordering
        # show most recent events first, but otherwise leave the ordering alone
        return [
            '-event__datetime' if o in ['event__datetime', 'event'] else o
            for o in ordering
        ]

    def get_deleted_objects(self, objs, request):
        if isinstance(objs, QuerySet):
            protected = self.filter_archived_events(objs)
            objs = self.exclude_archived_events(objs)
        else:
            protected = [o for o in objs if o.event.archived]
            objs = [o for o in objs if not o.event.archived]
        deleted_objects, model_count, perms_needed, other_protected = (
            super().get_deleted_objects(objs, request)
        )
        for p in protected:
            perms_needed.add(f'{p._meta.verbose_name} on Archived Event')
        return deleted_objects, model_count, perms_needed, other_protected

    def get_event_filter_key(self):
        return 'event'

    def filter_to_event(self, queryset, event):
        return queryset.filter(**{self.get_event_filter_key(): event})

    def filter_archived_events(self, queryset):
        return queryset.filter(**{f'{self.get_event_filter_key()}__archived': True})

    def exclude_archived_events(self, queryset):
        return queryset.exclude(**{f'{self.get_event_filter_key()}__archived': True})

    def get_search_results(self, request, queryset, search_term):
        parent_model = self.get_parent_model(request)
        if parent_model:
            queryset = self.filter_to_event(queryset, parent_model.event)
        elif request.resolver_match.view_name == 'admin:autocomplete':
            queryset = self.exclude_archived_events(queryset)
        return super().get_search_results(request, queryset, search_term)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and (
            obj is None or not obj.event.archived
        )

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and (
            obj is None or not obj.event.archived
        )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        event_field = form.base_fields.get('event', None)

        if event_field and not obj:
            event_field.initial = current_or_next_event_id()

        # this prevents the event field, if any, from allowing archived events as a choice, preventing a few edge cases
        #  as well as request tampering

        queryset = getattr(event_field, 'queryset', None)
        if queryset:
            form.base_fields['event'].queryset = queryset.filter(archived=False)
        for field in self.get_event_child_fields():
            queryset = getattr(form.base_fields.get(field, None), 'queryset', None)
            if queryset:
                # TODO: is there ever a case when this isn't the right lookup?
                form.base_fields[field].queryset = queryset.filter(
                    event__archived=False
                )
        return form

    def get_readonly_fields(self, request, obj=None):
        # ensures that a child object won't accidentally get moved off an archived event
        readonly_fields = tuple(super().get_readonly_fields(request, obj))
        if obj and obj.event.archived:
            readonly_fields += ('event', *self.get_event_child_fields())
        return readonly_fields

    def save_form(self, request, form, change):
        event = form.cleaned_data.get('event', form.instance.event)
        # this is a truly degenerate case
        # a user either has to be:
        # - adding a new child to event N
        # - changing an existing child to point to event N when it wasn't before
        # in addition to the following two conditions:
        # - event N was not archived when the user opened the form, but got archived before the user could save, OR
        #   the user tampered with the request
        # - was not caught by existing machinery (choice validation, etc.)
        if event and event.archived:
            raise PermissionDenied
        for field in self.get_event_child_fields():
            model = form.cleaned_data.get(field, getattr(form.instance, field))
            if model and model.event.archived:
                raise PermissionDenied
        return super().save_form(request, form, change)

    def get_event(self, obj):
        return obj and obj.event

    def get_event_child_fields(self):
        """
        a list of fields to consider when trying to move something to a new parent, when that parent belongs to an event
        """
        return getattr(self, 'event_child_fields', [])


class EventReadOnlyForm(ModelForm):
    def _get_validation_exclusions(self):
        # TODO: better way of making sure this doesn't get excluded?
        exclusions = super()._get_validation_exclusions()
        if 'event' in exclusions:
            exclusions.remove('event')
        return exclusions


class EventReadOnlyMixin:
    def get_readonly_fields(self, request, obj):
        readonly_fields = tuple(super().get_readonly_fields(request, obj))
        if obj:
            readonly_fields += ('event',)
        return readonly_fields

    def get_form(self, request, obj=None, *args, **kwargs):
        kwargs.setdefault('form', EventReadOnlyForm)
        assert issubclass(kwargs['form'], EventReadOnlyForm)
        return super().get_form(request, obj, *args, **kwargs)


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
        return tuple(list_display)

    def get_list_filter(self, request):
        list_filter = list(super().get_list_filter(request))
        if not request.user.has_perm('tracker.view_pending_donation'):
            list_filter.remove('donation__transactionstate')
        if (
            not request.user.has_perm('tracker.view_pending_donation')
            and 'donation__testdonation' in list_filter
        ):
            list_filter.remove('donation__testdonation')
        return tuple(list_filter)


class RelatedUserMixin:
    related_user_fields = ('user',)

    def get_related_user_fields(self):
        return tuple(self.related_user_fields)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        related_user_fields = self.get_related_user_fields()

        for field in related_user_fields:
            if field in form.base_fields:
                widget = form.base_fields[field].widget.widget
                widget.url_name = '%s:tracker_user_autocomplete'

        return form
