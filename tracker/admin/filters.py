from typing import Type

from django.contrib.admin import SimpleListFilter
from django.contrib.admin import models as admin_models
from django.db.models import Q

from tracker import models, search_feeds

from .util import ReadOffsetTokenPair


class PrizeListFilter(SimpleListFilter):
    title = 'feed'
    parameter_name = 'feed'

    def lookups(self, request, model_admin):
        return (
            ('unwon', 'Not Drawn'),
            ('won', 'Drawn'),
            ('current', 'Current'),
            ('future', 'Future'),
            ('todraw', 'Ready To Draw'),
        )

    def queryset(self, request, queryset):
        if self.value() is not None:
            feed, params = ReadOffsetTokenPair(self.value())
            params['noslice'] = True
            return search_feeds.apply_feed_filter(
                queryset, 'prize', feed, params, request.user
            )
        else:
            return queryset


class AdminActionLogEntryFlagFilter(SimpleListFilter):
    title = 'Action Type'
    parameter_name = 'action_flag'

    def lookups(self, request, model_admin):
        return (
            (admin_models.ADDITION, 'Added'),
            (admin_models.CHANGE, 'Changed'),
            (admin_models.DELETION, 'Deleted'),
        )

    def queryset(self, request, queryset):
        if self.value() is not None:
            flag = int(self.value())
            return queryset.filter(action_flag=flag)
        else:
            return queryset


def EventFilter(field, lookup=None) -> Type[SimpleListFilter]:
    """
    generates a filter class that filters on the specified field/lookup

    :param field: the keyword of the filter, and the field to use if lookup is not specified
    :param lookup: either None, in which case the filter is generated from field (e.g. filter(field__event=value), or a
        function that returns a query filter when provided with the value
    :return:
    """

    class Filter(SimpleListFilter):
        title = f'{field.capitalize()} by Event'
        parameter_name = f'{field}_by_event'

        def lookups(self, request, model_admin):
            return [(e.id, e.name) for e in models.Event.objects.all()]

        def queryset(self, request, queryset):
            value = self.value()
            if not value:
                return queryset

            if lookup:
                query_filter = lookup(value)
            else:
                query_filter = Q(**{f'{field}__event': value})

            return queryset.filter(query_filter).distinct()

    return Filter


class ParticipantFilter(SimpleListFilter):
    title = 'participant'
    parameter_name = 'participant'

    def lookups(self, request, model_admin):
        return []

    def has_output(self):
        return True

    def queryset(self, request, queryset):
        if (value := self.value()) is not None:
            try:
                value = int(value)
            except ValueError:
                value = models.Talent.objects.get_by_natural_key(value) or value
            return queryset.filter(
                Q(runners=value) | Q(hosts=value) | Q(commentators=value)
            )
        else:
            return queryset


class RunListFilter(SimpleListFilter):
    title = 'feed'
    parameter_name = 'feed'

    def lookups(self, request, model_admin):
        return (
            ('current', 'Current'),
            ('future', 'Future'),
            ('recent-60', 'Last Hour'),
            ('recent-180', 'Last 3 Hours'),
            ('recent-300', 'Last 5 Hours'),
            ('future-60', 'Next Hour'),
            ('future-180', 'Next 3 Hours'),
            ('future-300', 'Next 5 Hours'),
        )

    def queryset(self, request, queryset):
        if self.value() is not None:
            feed, params = ReadOffsetTokenPair(self.value())
            params['noslice'] = True
            return search_feeds.apply_feed_filter(
                queryset, 'run', feed, params, request.user
            )
        else:
            return queryset


class DonationListFilter(SimpleListFilter):
    title = 'feed'
    parameter_name = 'feed'

    def lookups(self, request, model_admin):
        return (
            ('toprocess', 'To Process'),
            ('toread', 'To Read'),
            ('recent-5', 'Last 5 Minutes'),
            ('recent-10', 'Last 10 Minutes'),
            ('recent-30', 'Last 30 Minutes'),
            ('recent-60', 'Last Hour'),
            ('recent-180', 'Last 3 Hours'),
        )

    def queryset(self, request, queryset):
        if self.value() is not None:
            feed, params = ReadOffsetTokenPair(self.value())
            params['noslice'] = True
            return search_feeds.apply_feed_filter(
                queryset, 'donation', feed, params, request.user
            )
        else:
            return queryset


class BidListFilter(SimpleListFilter):
    title = 'feed'
    parameter_name = 'feed'

    def lookups(self, request, model_admin):
        return (
            ('current', 'Current'),
            ('future', 'Future'),
            ('open', 'Open'),
            ('closed', 'Closed'),
        )

    def queryset(self, request, queryset):
        if self.value() is not None:
            feed, params = ReadOffsetTokenPair(self.value())
            params['noslice'] = True
            return search_feeds.apply_feed_filter(
                queryset, 'bid', feed, params, request.user
            )
        else:
            return queryset


class BidParentFilter(SimpleListFilter):
    title = 'top level'
    parameter_name = 'toplevel'

    def lookups(self, request, model_admin):
        return ((1, 'Yes'), (0, 'No'))

    def queryset(self, request, queryset):
        try:
            queryset = queryset.filter(
                parent__isnull=True if int(self.value()) == 1 else False
            )
        except (
            TypeError,
            ValueError,
        ):  # self.value cannot be converted to int for whatever reason
            pass
        return queryset
