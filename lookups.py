from ajax_select import LookupChannel
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe

import tracker.search_filters as filters
import tracker.viewutil as viewutil
from tracker.models import (
    Bid,
    Country,
    CountryRegion,
    Donation,
    Donor,
    Event,
    Prize,
    Runner,
    SpeedRun,
)

"""
In order to use these lookups properly with the admin, you will need to install/enable the 'ajax_select'
django module, and also add an AJAX_LOOKUP_CHANNELS table (the table of all
lookups used by this application are in tracker/ajax_lookup_channels.py)

They can be imported with the line:

from tracker.ajax_lookup_channels import AJAX_LOOKUP_CHANNELS
"""


class UserLookup(LookupChannel):
    def __init__(self, *args, **kwargs):
        self.model = get_user_model()
        super(UserLookup, self).__init__(*args, **kwargs)

    def get_query(self, q, request):
        if not request.user.has_perm('tracker.can_search'):
            raise PermissionDenied
        return self.model.objects.filter(username__icontains=q)

    def get_result(self, obj):
        return obj.username

    def format_match(self, obj):
        return escape(obj.username)

    def can_add(self, user, source_model):
        # avoid in-line addition of users by accident
        return False


class CountryLookup(LookupChannel):
    model = Country

    def get_query(self, q, request):
        return Country.objects.filter(name__icontains=q)

    def get_result(self, obj):
        return str(obj)

    def format_match(self, obj):
        return escape(str(obj))

    def can_add(self, user, source_model):
        # Presumably, we don't want to add countries typically
        return False


class CountryRegionLookup(LookupChannel):
    model = CountryRegion

    def get_query(self, q, request):
        return CountryRegion.objects.filter(
            Q(name__icontains=q) | Q(country__name__icontains=q)
        )

    def get_result(self, obj):
        return str(obj)

    def format_match(self, obj):
        return escape(str(obj))


class GenericLookup(LookupChannel):
    use_lock = False
    use_event = False
    extra_params = {}

    def get_extra_params(self, request):
        return self.extra_params

    def get_query(self, q, request):
        params = {'q': q}
        params.update(self.get_extra_params(request))
        event = viewutil.get_selected_event(request)
        if event and self.use_event:
            params['event'] = event.id
        model = getattr(self, 'model_name', self.model)
        if self.use_lock and not request.user.has_perm(
            'tracker.can_edit_locked_events'
        ):
            params['locked'] = False
        return filters.run_model_query(model, params, request.user)

    def get_result(self, obj):
        return str(obj)

    def format_match(self, obj):
        return escape(str(obj))

    # returning the admin URL reduces the genericity of our solution a little bit, but this can be solved
    # by using distinct lookups for admin/non-admin applications (which we should do regardless since
    # non-admin search should be different)
    def format_item_display(self, obj):
        result = '<a href="{0}">{1}</a>'.format(
            reverse(
                'admin:tracker_{0}_change'.format(obj._meta.model_name), args=[obj.pk]
            ),
            escape(str(obj)),
        )
        return mark_safe(result)


class BidLookup(GenericLookup):
    use_event = True
    use_lock = True
    model = Bid
    model_name = 'bid'
    extra_params = {'feed': 'all'}


class AllBidLookup(GenericLookup):
    use_event = True
    use_lock = True
    model = Bid
    model_name = 'allbids'
    extra_params = {'feed': 'all'}


class BidTargetLookup(GenericLookup):
    model = Bid
    model_name = 'bidtarget'
    use_event = True
    use_lock = True
    extra_params = {'feed': 'all'}


class DonationLookup(GenericLookup):
    model = Donation
    use_event = True
    use_lock = True


class DonorLookup(GenericLookup):
    model = Donor


class PrizeLookup(GenericLookup):
    model = Prize
    use_event = True


class RunLookup(GenericLookup):
    model = SpeedRun
    use_event = True
    use_lock = True


class EventLookup(GenericLookup):
    model = Event
    use_lock = True


class RunnerLookup(GenericLookup):
    model = Runner
