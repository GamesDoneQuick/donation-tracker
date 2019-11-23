import json
from datetime import datetime, timedelta

import django.forms as djforms
from ajax_select import make_ajax_field
from ajax_select.admin import AjaxSelectAdmin
from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required, REDIRECT_FIELD_NAME
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, redirect
from django.utils.safestring import mark_safe

import tracker.filters as filters
import tracker.forms as forms
import tracker.logutil as logutil
import tracker.models
import tracker.prizemail as prizemail
import tracker.prizeutil as prizeutil
import tracker.views as views
import tracker.viewutil as viewutil


def admin_auth(
    perm=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url='admin:login'
):
    def impl_dec(viewFunc):
        wrapFunc = viewFunc
        if perm:
            wrapFunc = permission_required(perm, raise_exception=True)(viewFunc)
        return staff_member_required(
            wrapFunc, redirect_field_name=redirect_field_name, login_url=login_url
        )

    return impl_dec


def reverse_lazy(url):
    return lambda: reverse(url)


def latest_event_id():
    try:
        return tracker.models.Event.objects.latest().id
    except tracker.models.Event.DoesNotExist:
        return 0


class CustomModelAdmin(AjaxSelectAdmin):
    pass


class CustomStackedInline(admin.StackedInline):
    # Adds an link that lets you edit an in-line linked object
    def edit_link(self, instance):
        if instance.id is not None:
            url = reverse(
                'admin:{label}_{merge}_change'.format(
                    label=instance._meta.app_label, merge=instance._meta.model_name
                ),
                args=[instance.id],
            )
            return mark_safe('<a href="{u}">Edit</a>'.format(u=url))
        else:
            return mark_safe('Not Saved Yet')


def ReadOffsetTokenPair(value):
    toks = value.split('-')
    feed = toks[0]
    params = {}
    if len(toks) > 1:
        params['delta'] = toks[1]
    return feed, params


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
            return filters.apply_feed_filter(
                queryset, 'donation', feed, params, user=request.user, noslice=True
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
            return filters.apply_feed_filter(
                queryset, 'bid', feed, params, request.user, noslice=True
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


class BidSuggestionListFilter(SimpleListFilter):
    title = 'feed'
    parameter_name = 'feed'

    def lookups(self, request, model_admin):
        return (('expired', 'Expired'),)

    def queryset(self, request, queryset):
        if self.value() is not None:
            feed, params = ReadOffsetTokenPair(self.value())
            return filters.apply_feed_filter(
                queryset, 'bidsuggestion', feed, params, request.user, noslice=True
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
            return filters.apply_feed_filter(
                queryset, 'run', feed, params, user=request.user, noslice=True
            )
        else:
            return queryset


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
            return filters.apply_feed_filter(
                queryset, 'prize', feed, params, request.user, noslice=True
            )
        else:
            return queryset


def bid_open_action(modeladmin, request, queryset):
    bid_set_state_action(modeladmin, request, queryset, 'OPENED')


bid_open_action.short_description = 'Set Bids as OPENED'


def bid_close_action(modeladmin, request, queryset):
    bid_set_state_action(modeladmin, request, queryset, 'CLOSED')


bid_close_action.short_description = 'Set Bids as CLOSED'


def bid_hidden_action(modeladmin, request, queryset):
    bid_set_state_action(modeladmin, request, queryset, 'HIDDEN')


bid_hidden_action.short_description = 'Set Bids as HIDDEN'


def bid_set_state_action(modeladmin, request, queryset, value, recursive=False):
    if not request.user.has_perm('tracker.can_edit_locked_event'):
        unchanged = queryset.filter(event__locked=True)
        if unchanged.exists():
            messages.warning(
                request,
                '%d bid(s) unchanged due to the event being locked.'
                % unchanged.count(),
            )
        queryset = queryset.filter(event__locked=False)
    if not recursive:
        unchanged = queryset.filter(parent__isnull=False)
        if unchanged.exists():
            messages.warning(
                request,
                '%d bid(s) possibly unchanged because you can only use the dropdown on top level bids.'
                % unchanged.count(),
            )
        queryset = queryset.filter(parent__isnull=True)
    total = queryset.count()
    for b in queryset:
        b.state = value
        b.clean()
        b.save()  # can't use queryset.update because that doesn't send the post_save signals
        logutil.change(request, b, ['state'])
    if total and not recursive:
        messages.success(request, '%d bid(s) changed to %s.' % (total, value))
    return total


class CountryRegionForm(djforms.ModelForm):
    country = make_ajax_field(tracker.models.CountryRegion, 'country', 'country')

    class Meta:
        model = tracker.models.CountryRegion
        exclude = ('', '')


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
        (None, {'fields': ['name', 'country'],}),
    ]


class BidForm(djforms.ModelForm):
    speedrun = make_ajax_field(tracker.models.Bid, 'speedrun', 'run')
    event = make_ajax_field(
        tracker.models.Bid, 'event', 'event', initial=latest_event_id
    )
    biddependency = make_ajax_field(tracker.models.Bid, 'biddependency', 'allbids')


class BidInline(CustomStackedInline):
    model = tracker.models.Bid
    fieldsets = [
        (
            None,
            {
                'fields': [
                    'name',
                    'description',
                    'shortdescription',
                    'istarget',
                    'goal',
                    'state',
                    'total',
                    'edit_link',
                ],
            },
        )
    ]
    extra = 0
    readonly_fields = (
        'total',
        'edit_link',
    )
    ordering = ('-total', 'name')


class BidOptionInline(BidInline):
    verbose_name_plural = 'Options'
    verbose_name = 'Option'
    fk_name = 'parent'


class BidDependentsInline(BidInline):
    verbose_name_plural = 'Dependent Bids'
    verbose_name = 'Dependent Bid'
    fk_name = 'biddependency'


class BidAdmin(CustomModelAdmin):
    form = BidForm
    list_display = (
        'name',
        'parentlong',
        'istarget',
        'goal',
        'total',
        'description',
        'state',
        'biddependency',
    )
    list_display_links = ('parentlong', 'biddependency')
    search_fields = (
        'name',
        'speedrun__name',
        'description',
        'shortdescription',
        'parent__name',
    )
    list_filter = (
        'speedrun__event',
        'state',
        'istarget',
        BidParentFilter,
        BidListFilter,
    )
    readonly_fields = ('parent', 'parent_', 'total')
    fieldsets = [
        (
            None,
            {
                'fields': [
                    'name',
                    'state',
                    'description',
                    'shortdescription',
                    'goal',
                    'istarget',
                    'allowuseroptions',
                    'option_max_length',
                    'revealedtime',
                    'total',
                ]
            },
        ),
        ('Link Info', {'fields': ['event', 'speedrun', 'parent_', 'biddependency']}),
    ]
    inlines = [BidOptionInline, BidDependentsInline]

    def parentlong(self, obj):
        return str(obj.parent or obj.speedrun or obj.event)

    def parent_(self, obj):
        targetObject = None
        if obj.parent:
            targetObject = obj.parent
        elif obj.speedrun:
            targetObject = obj.speedrun
        elif obj.event:
            targetObject = obj.event
        if targetObject:
            return mark_safe(
                '<a href={0}>{1}</a>'.format(
                    str(viewutil.admin_url(targetObject)), targetObject
                )
            )
        else:
            return '<None>'

    parentlong.short_description = 'Parent'

    def get_queryset(self, request):
        event = viewutil.get_selected_event(request)
        params = {}
        if event:
            params['event'] = event.id
        if not request.user.has_perm('tracker.can_edit_locked_events'):
            params['locked'] = False
        return filters.run_model_query(
            'allbids', params, user=request.user, mode='admin'
        )

    def has_add_permission(self, request):
        return request.user.has_perm('tracker.top_level_bid')

    def has_change_permission(self, request, obj=None):
        return super(BidAdmin, self).has_change_permission(request, obj) and (
            obj is None
            or request.user.has_perm('tracker.can_edit_locked_events')
            or not obj.event.locked
        )

    def has_delete_permission(self, request, obj=None):
        return super(BidAdmin, self).has_delete_permission(request, obj) and (
            obj is None
            or (
                (
                    request.user.has_perm('tracker.can_edit_locked_events')
                    or not obj.event.locked
                )
                and (request.user.has_perm('tracker.delete_all_bids') or not obj.total)
            )
        )

    def merge_bids(self, request, queryset):
        bids = queryset
        for bid in bids:
            if not bid.istarget:
                self.message_user(
                    request,
                    'All merged bids must be target bids.',
                    level=messages.ERROR,
                )
                return HttpResponseRedirect(reverse('admin:tracker_bid_changelist'))
        return HttpResponseRedirect(
            reverse('admin:merge_bids')
            + '?objects='
            + ','.join(str(o.id) for o in bids)
        )

    merge_bids.short_description = 'Merge selected bids'
    actions = [bid_open_action, bid_close_action, bid_hidden_action, merge_bids]

    def get_actions(self, request):
        actions = super(BidAdmin, self).get_actions(request)
        if (
            not request.user.has_perm('tracker.delete_all_bids')
            and 'delete_selected' in actions
        ):
            del actions['delete_selected']
        return actions


@admin_auth('tracker.change_bid')
def merge_bids_view(request, *args, **kwargs):
    if request.method == 'POST':
        objects = [int(x) for x in request.POST['objects'].split(',')]
        form = forms.MergeObjectsForm(
            model=tracker.models.Bid, objects=objects, data=request.POST
        )
        if form.is_valid():
            viewutil.merge_bids(form.cleaned_data['root'], form.cleaned_data['objects'])
            logutil.change(
                request,
                form.cleaned_data['root'],
                'Merged bid {0} with {1}'.format(
                    form.cleaned_data['root'],
                    ','.join([str(d) for d in form.cleaned_data['objects']]),
                ),
            )
            return HttpResponseRedirect(reverse('admin:tracker_bid_changelist'))
    else:
        objects = [int(x) for x in request.GET['objects'].split(',')]
        form = forms.MergeObjectsForm(model=tracker.models.Bid, objects=objects)
    return render(request, 'admin/merge_bids.html', {'form': form})


class BidSuggestionForm(djforms.ModelForm):
    bid = make_ajax_field(tracker.models.BidSuggestion, 'bid', 'bidtarget')


class BidSuggestionAdmin(CustomModelAdmin):
    form = BidSuggestionForm
    list_display = ('name', 'bid')
    search_fields = ('name', 'bid__name', 'bid__description')
    list_filter = (
        'bid__state',
        'bid__speedrun__event',
        'bid__event',
        BidSuggestionListFilter,
    )

    def get_queryset(self, request):
        event = viewutil.get_selected_event(request)
        params = {}
        if not request.user.has_perm('tracker.can_edit_locked_events'):
            params['locked'] = False
        if event:
            params['event'] = event.id
        return filters.run_model_query(
            'bidsuggestion', params, user=request.user, mode='admin'
        )


class DonationBidForm(djforms.ModelForm):
    bid = make_ajax_field(tracker.models.DonationBid, 'bid', 'bidtarget')
    donation = make_ajax_field(tracker.models.DonationBid, 'donation', 'donation')


class DonationBidInline(CustomStackedInline):
    form = DonationBidForm
    model = tracker.models.DonationBid
    extra = 0
    max_num = 100
    readonly_fields = ('edit_link',)


class DonationBidAdmin(CustomModelAdmin):
    form = DonationBidForm
    list_display = ('bid', 'donation', 'amount')

    def get_queryset(self, request):
        event = viewutil.get_selected_event(request)
        params = {}
        if not request.user.has_perm('tracker.can_edit_locked_events'):
            params['locked'] = False
        if event:
            params['event'] = event.id
        return filters.run_model_query(
            'donationbid', params, user=request.user, mode='admin'
        )


class DonationForm(djforms.ModelForm):
    donor = make_ajax_field(tracker.models.Donation, 'donor', 'donor')
    event = make_ajax_field(
        tracker.models.Donation, 'event', 'event', initial=latest_event_id
    )

    class Meta:
        model = tracker.models.Donation
        exclude = ('', '')


class DonationInline(CustomStackedInline):
    form = DonationForm
    model = tracker.models.Donation
    extra = 0
    readonly_fields = ('edit_link',)


def mass_assign_action(self, request, queryset, field, value):
    queryset.update(**{field: value})
    self.message_user(request, 'Updated %s to %s' % (field, value))


class DonationAdmin(CustomModelAdmin):
    form = DonationForm
    list_display = (
        'id',
        'visible_donor_name',
        'amount',
        'comment',
        'commentlanguage',
        'timereceived',
        'event',
        'domain',
        'transactionstate',
        'bidstate',
        'readstate',
        'commentstate',
    )
    list_editable = ('transactionstate', 'bidstate', 'readstate', 'commentstate')
    search_fields_base = ('donor__alias', 'amount', 'comment', 'modcomment')
    list_filter = (
        'event',
        'transactionstate',
        'readstate',
        'commentstate',
        'bidstate',
        'commentlanguage',
        DonationListFilter,
    )
    readonly_fields = ['domainId']
    inlines = (DonationBidInline,)
    fieldsets = [
        (None, {'fields': ('donor', 'event', 'timereceived')}),
        ('Comment State', {'fields': ('comment', 'modcomment')}),
        (
            'Donation State',
            {
                'fields': (
                    ('transactionstate', 'bidstate', 'readstate', 'commentstate'),
                )
            },
        ),
        ('Financial', {'fields': (('amount', 'fee', 'currency', 'testdonation'),)}),
        (
            'Extra Donor Info',
            {
                'fields': (
                    (
                        'requestedvisibility',
                        'requestedalias',
                        'requestedemail',
                        'requestedsolicitemail',
                    ),
                )
            },
        ),
        ('Other', {'fields': (('domain', 'domainId'),)}),
    ]

    def visible_donor_name(self, obj):
        if obj.donor:
            return obj.donor.visible_name()
        else:
            return None

    def set_readstate_ready(self, request, queryset):
        mass_assign_action(self, request, queryset, 'readstate', 'READY')

    set_readstate_ready.short_description = 'Set Read state to ready to read.'

    def set_readstate_ignored(self, request, queryset):
        mass_assign_action(self, request, queryset, 'readstate', 'IGNORED')

    set_readstate_ignored.short_description = 'Set Read state to ignored.'

    def set_readstate_read(self, request, queryset):
        mass_assign_action(self, request, queryset, 'readstate', 'READ')

    set_readstate_read.short_description = 'Set Read state to read.'

    def set_commentstate_approved(self, request, queryset):
        mass_assign_action(self, request, queryset, 'commentstate', 'APPROVED')

    set_commentstate_approved.short_description = 'Set Comment state to approved.'

    def set_commentstate_denied(self, request, queryset):
        mass_assign_action(self, request, queryset, 'commentstate', 'DENIED')

    set_commentstate_denied.short_description = 'Set Comment state to denied.'

    def cleanup_orphaned_donations(self, request, queryset):
        count = 0
        for donation in queryset.filter(
            donor=None,
            domain='PAYPAL',
            transactionstate='PENDING',
            timereceived__lte=datetime.utcnow() - timedelta(hours=8),
        ):
            for bid in donation.bids.all():
                bid.delete()
            donation.delete()
            count += 1
        self.message_user(request, 'Deleted %d donations.' % count)
        viewutil.tracker_log(
            'donation',
            'Deleted {0} orphaned donations'.format(count),
            user=request.user,
        )

    cleanup_orphaned_donations.short_description = 'Clear out incomplete donations.'

    def get_list_display(self, request):
        ret = list(self.list_display)
        if not request.user.has_perm('tracker.delete_all_donations'):
            ret.remove('transactionstate')
        return ret

    def get_readonly_fields(self, request, obj=None):
        perm = request.user.has_perm('tracker.delete_all_donations')
        ret = list(self.readonly_fields)
        if not perm:
            ret.append('domain')
            ret.append('fee')
            ret.append('transactionstate')
            ret.append('testdonation')
            if obj and obj.domain != 'LOCAL':
                ret.append('donor')
                ret.append('event')
                ret.append('timereceived')
                ret.append('amount')
                ret.append('currency')
        return ret

    def has_change_permission(self, request, obj=None):
        return super(DonationAdmin, self).has_change_permission(request, obj) and (
            obj is None
            or request.user.has_perm('tracker.can_edit_locked_events')
            or not obj.event.locked
        )

    def has_delete_permission(self, request, obj=None):
        return super(DonationAdmin, self).has_delete_permission(request, obj) and (
            obj is None
            or obj.domain == 'LOCAL'
            or request.user.has_perm('tracker.delete_all_donations')
        )

    def get_search_fields(self, request):
        search_fields = list(self.search_fields_base)
        if request.user.has_perm('tracker.view_emails'):
            search_fields += ['donor__email', 'donor__paypalemail']
        if request.user.has_perm('tracker.view_usernames'):
            search_fields += ['donor__firstname', 'donor__lastname']
        return search_fields

    def get_queryset(self, request):
        event = viewutil.get_selected_event(request)
        params = {}
        if not request.user.has_perm('tracker.can_edit_locked_events'):
            params['locked'] = False
        if event:
            params['event'] = event.id
        return filters.run_model_query(
            'donation', params, user=request.user, mode='admin'
        )

    actions = [
        set_readstate_ready,
        set_readstate_ignored,
        set_readstate_read,
        set_commentstate_approved,
        set_commentstate_denied,
        cleanup_orphaned_donations,
    ]

    def get_actions(self, request):
        actions = super(DonationAdmin, self).get_actions(request)
        if (
            not request.user.has_perm('tracker.delete_all_donations')
            and 'delete_selected' in actions
        ):
            del actions['delete_selected']
        return actions


class PrizeWinnerForm(djforms.ModelForm):
    winner = make_ajax_field(tracker.models.PrizeWinner, 'winner', 'donor')
    prize = make_ajax_field(tracker.models.PrizeWinner, 'prize', 'prize')

    class Meta:
        model = tracker.models.PrizeWinner
        exclude = ('', '')


class PrizeWinnerInline(CustomStackedInline):
    form = PrizeWinnerForm
    model = tracker.models.PrizeWinner
    readonly_fields = ['winner_email', 'edit_link']

    def winner_email(self, obj):
        return obj.winner.email

    extra = 0


class PrizeWinnerAdmin(CustomModelAdmin):
    form = PrizeWinnerForm
    search_fields = ['prize__name', 'winner__email']
    list_display = ['__str__', 'prize', 'winner']
    readonly_fields = [
        'winner_email',
    ]
    fieldsets = [
        (
            None,
            {
                'fields': [
                    'prize',
                    'winner',
                    'winner_email',
                    'emailsent',
                    'pendingcount',
                    'acceptcount',
                    'declinecount',
                    'acceptdeadline',
                ],
            },
        ),
        (
            'Shipping Info',
            {
                'fields': [
                    'acceptemailsentcount',
                    'shippingstate',
                    'shippingemailsent',
                    'trackingnumber',
                    'shippingcost',
                    'shipping_receipt_url',
                ]
            },
        ),
    ]

    def winner_email(self, obj):
        return obj.winner.email

    def get_queryset(self, request):
        event = viewutil.get_selected_event(request)
        params = {}
        if not request.user.has_perm('tracker.can_edit_locked_events'):
            params['locked'] = False
        if event:
            params['event'] = event.id
        return filters.run_model_query(
            'prizewinner', params, user=request.user, mode='admin'
        )


class DonorPrizeEntryForm(djforms.ModelForm):
    donor = make_ajax_field(tracker.models.DonorPrizeEntry, 'donor', 'donor')
    prize = make_ajax_field(tracker.models.DonorPrizeEntry, 'prize', 'prize')

    class Meta:
        model = tracker.models.DonorPrizeEntry
        exclude = ('', '')


class DonorPrizeEntryInline(CustomStackedInline):
    form = DonorPrizeEntryForm
    model = tracker.models.DonorPrizeEntry
    readonly_fields = ['edit_link']
    extra = 0


class DonorPrizeEntryAdmin(CustomModelAdmin):
    form = DonorPrizeEntryForm
    model = tracker.models.DonorPrizeEntry
    search_fields = [
        'prize__name',
        'donor__email',
        'donor__alias',
        'donor__firstname',
        'donor__lastname',
    ]
    list_display = ['prize', 'donor', 'weight']
    list_filter = ['prize__event', 'prize', 'donor']
    fieldsets = [
        (None, {'fields': ['donor', 'prize', 'weight']}),
    ]

    def get_queryset(self, request):
        event = viewutil.get_selected_event(request)
        params = {}
        if not request.user.has_perm('tracker.can_edit_locked_events'):
            params['locked'] = False
        if event:
            params['event'] = event.id
        return filters.run_model_query(
            'prizeentry', params, user=request.user, mode='admin'
        )


class DonorForm(djforms.ModelForm):
    addresscountry = make_ajax_field(tracker.models.Donor, 'addresscountry', 'country')
    user = make_ajax_field(tracker.models.Donor, 'user', 'user')

    class Meta:
        model = tracker.models.Donor
        exclude = ('', '')


class DonorAdmin(CustomModelAdmin):
    form = DonorForm
    search_fields = ('email', 'paypalemail', 'alias', 'firstname', 'lastname')
    list_filter = ('donation__event', 'visibility')
    readonly_fields = ('visible_name',)
    list_display = ('__str__', 'visible_name', 'alias', 'visibility')
    fieldsets = [
        (
            None,
            {
                'fields': [
                    'email',
                    'alias',
                    'firstname',
                    'lastname',
                    'visibility',
                    'visible_name',
                    'user',
                    'solicitemail',
                ]
            },
        ),
        ('Donor Info', {'classes': ['collapse'], 'fields': ['paypalemail']}),
        (
            'Address Info',
            {
                'classes': ['collapse'],
                'fields': [
                    'addressstreet',
                    'addresscity',
                    'addressstate',
                    'addresscountry',
                    'addresszip',
                ],
            },
        ),
    ]
    inlines = [
        DonationInline,
        PrizeWinnerInline,
        DonorPrizeEntryInline,
    ]

    def visible_name(self, obj):
        return obj.visible_name()

    def merge_donors(self, request, queryset):
        donors = queryset
        return HttpResponseRedirect(
            reverse('admin:merge_donors')
            + '?objects='
            + ','.join(str(o.id) for o in donors)
        )

    merge_donors.short_description = 'Merge selected donors'
    actions = [merge_donors]


@admin_auth('tracker.change_donor')
def merge_donors_view(request, *args, **kwargs):
    if request.method == 'POST':
        objects = [int(x) for x in request.POST['objects'].split(',')]
        form = forms.MergeObjectsForm(
            model=tracker.models.Donor, objects=objects, data=request.POST
        )
        if form.is_valid():
            viewutil.merge_donors(
                form.cleaned_data['root'], form.cleaned_data['objects']
            )
            logutil.change(
                request,
                form.cleaned_data['root'],
                'Merged donor {0} with {1}'.format(
                    form.cleaned_data['root'],
                    ','.join([str(d) for d in form.cleaned_data['objects']]),
                ),
            )
            return HttpResponseRedirect(reverse('admin:tracker_donor_changelist'))
    else:
        objects = [int(x) for x in request.GET['objects'].split(',')]
        form = forms.MergeObjectsForm(model=tracker.models.Donor, objects=objects)
    return render(request, 'admin/merge_donors.html', {'form': form})


class EventForm(djforms.ModelForm):
    allowed_prize_countries = make_ajax_field(
        tracker.models.Event, 'allowed_prize_countries', 'country'
    )
    disallowed_prize_regions = make_ajax_field(
        tracker.models.Event, 'disallowed_prize_regions', 'countryregion'
    )
    prizecoordinator = make_ajax_field(tracker.models.Event, 'prizecoordinator', 'user')

    class Meta:
        model = tracker.models.Event
        exclude = ('', '')


class EventBidInline(BidInline):
    def get_queryset(self, request):
        qs = super(EventBidInline, self).get_queryset(request)
        return qs.filter(speedrun=None)


class EventAdmin(CustomModelAdmin):
    form = EventForm
    search_fields = ('short', 'name')
    inlines = [EventBidInline]
    list_display = ['name', 'locked', 'allow_donations']
    list_editable = ['locked', 'allow_donations']
    readonly_fields = ['scheduleid']
    fieldsets = [
        (
            None,
            {
                'fields': [
                    'short',
                    'name',
                    'receivername',
                    'targetamount',
                    'use_one_step_screening',
                    'minimumdonation',
                    'auto_approve_threshold',
                    'datetime',
                    'timezone',
                    'locked',
                    'allow_donations',
                ]
            },
        ),
        (
            'Paypal',
            {'classes': ['collapse'], 'fields': ['paypalemail', 'paypalcurrency',]},
        ),
        (
            'Donation Autoreply',
            {
                'classes': ['collapse',],
                'fields': [
                    'donationemailsender',
                    'donationemailtemplate',
                    'pendingdonationemailtemplate',
                ],
            },
        ),
        (
            'Prize Management',
            {
                'classes': ['collapse',],
                'fields': [
                    'prize_accept_deadline_delta',
                    'prizecoordinator',
                    'allowed_prize_countries',
                    'disallowed_prize_regions',
                    'prizecontributoremailtemplate',
                    'prizewinneremailtemplate',
                    'prizewinneracceptemailtemplate',
                    'prizeshippedemailtemplate',
                ],
            },
        ),
        ('Google Document', {'classes': ['collapse'], 'fields': ['scheduleid']}),
    ]


class PostbackURLForm(djforms.ModelForm):
    event = make_ajax_field(
        tracker.models.PostbackURL, 'event', 'event', initial=latest_event_id
    )

    class Meta:
        model = tracker.models.PostbackURL
        exclude = ('', '')


class PostbackURLAdmin(CustomModelAdmin):
    form = PostbackURLForm
    search_fields = ('url',)
    list_filter = ('event',)
    list_display = ('url', 'event')
    fieldsets = [(None, {'fields': ['event', 'url']})]

    def get_queryset(self, request):
        event = viewutil.get_selected_event(request)
        if event:
            return tracker.models.PostbackURL.objects.filter(event=event)
        else:
            return tracker.models.PostbackURL.objects.all()


class PrizeForm(djforms.ModelForm):
    event = make_ajax_field(
        tracker.models.Prize, 'event', 'event', initial=latest_event_id
    )
    startrun = make_ajax_field(tracker.models.Prize, 'startrun', 'run')
    endrun = make_ajax_field(tracker.models.Prize, 'endrun', 'run')
    handler = make_ajax_field(tracker.models.Prize, 'handler', 'user')
    allowed_prize_countries = make_ajax_field(
        tracker.models.Prize, 'allowed_prize_countries', 'country'
    )
    disallowed_prize_regions = make_ajax_field(
        tracker.models.Prize, 'disallowed_prize_regions', 'countryregion'
    )

    class Meta:
        model = tracker.models.Prize
        exclude = ('', '')


class PrizeInline(CustomStackedInline):
    model = tracker.models.Prize
    form = PrizeForm
    fk_name = 'endrun'
    extra = 0
    fields = [
        'name',
        'description',
        'shortdescription',
        'handler',
        'image',
        'altimage',
        'event',
        'state',
        'allowed_prize_countries',
        'disallowed_prize_regions',
        'edit_link',
    ]
    readonly_fields = ('edit_link',)


class PrizeAdmin(CustomModelAdmin):
    form = PrizeForm
    list_display = (
        'name',
        'category',
        'bidrange',
        'games',
        'start_draw_time',
        'end_draw_time',
        'sumdonations',
        'randomdraw',
        'event',
        'winners_',
        'provider',
        'handler',
        'key_code',
        'claimed',
        'unclaimed',
    )
    list_filter = ('event', 'category', 'state', PrizeListFilter)
    fieldsets = [
        (
            None,
            {
                'fields': [
                    'name',
                    'description',
                    'shortdescription',
                    'image',
                    'altimage',
                    'event',
                    'category',
                    'requiresshipping',
                    'handler',
                    'key_code',
                ]
            },
        ),
        (
            'Contributor Information',
            {
                'fields': [
                    'provider',
                    'creator',
                    'creatoremail',
                    'creatorwebsite',
                    'extrainfo',
                    'estimatedvalue',
                    'acceptemailsent',
                    'state',
                    'reviewnotes',
                ]
            },
        ),
        (
            'Drawing Parameters',
            {
                'classes': ['collapse'],
                'fields': [
                    'maxwinners',
                    'maxmultiwin',
                    'minimumbid',
                    'maximumbid',
                    'sumdonations',
                    'randomdraw',
                    'startrun',
                    'endrun',
                    'starttime',
                    'endtime',
                    'custom_country_filter',
                    'allowed_prize_countries',
                    'disallowed_prize_regions',
                ],
            },
        ),
    ]
    search_fields = (
        'name',
        'description',
        'shortdescription',
        'provider',
        'handler__username',
        'handler__email',
        'handler__last_name',
        'handler__first_name',
        'prizewinner__winner__firstname',
        'prizewinner__winner__lastname',
        'prizewinner__winner__alias',
        'prizewinner__winner__email',
    )
    inlines = [PrizeWinnerInline]

    def winners_(self, obj):
        winners = obj.get_winners()
        if obj.key_code:
            return len(winners)
        elif len(winners) > 0:
            return '; '.join(str(x) for x in winners)
        else:
            return 'None'

    def claimed(self, obj):
        if obj.key_code:
            return obj.prizekey_set.exclude(prize_winner=None).count()
        else:
            return 'N/A'

    def unclaimed(self, obj):
        if obj.key_code:
            return obj.prizekey_set.filter(prize_winner=None).count()
        else:
            return 'N/A'

    def bidrange(self, obj):
        s = str(obj.minimumbid)
        if obj.minimumbid != obj.maximumbid:
            if obj.maximumbid is None:
                max = 'Infinite'
            else:
                max = str(obj.maximumbid)
            s += ' <--> ' + max
        return s

    bidrange.short_description = 'Bid Range'

    def games(self, obj):
        if obj.startrun is None:
            return ''
        else:
            s = str(obj.startrun.name_with_category())
            if obj.startrun != obj.endrun:
                s += ' <--> ' + str(obj.endrun.name_with_category())

    def draw_prize_internal(self, request, queryset, limit):
        numDrawn = 0
        for prize in queryset:
            if prize.key_code:
                drawn, msg = prizeutil.draw_keys(prize)
                if drawn:
                    numDrawn += len(msg['winners'])
                else:
                    messages.error(request, msg['error'])
            else:
                if limit is None:
                    limit = prize.maxwinners
                numToDraw = min(limit, prize.maxwinners - prize.current_win_count())
                drawingError = False
                while not drawingError and numDrawn < numToDraw:
                    drawn, msg = prizeutil.draw_prize(prize)
                    if not drawn:
                        self.message_user(request, msg['error'], level=messages.ERROR)
                        drawingError = True
                    else:
                        numDrawn += 1
        if numDrawn > 0:
            self.message_user(request, '%d prizes drawn.' % numDrawn)

    def draw_prize_once_action(self, request, queryset):
        self.draw_prize_internal(request, queryset, 1)

    draw_prize_once_action.short_description = (
        'Draw a SINGLE winner for the selected prizes'
    )

    def draw_prize_action(self, request, queryset):
        self.draw_prize_internal(request, queryset, None)

    draw_prize_action.short_description = 'Draw (all) winner(s) for the selected prizes'

    def import_keys_action(self, request, queryset):
        if queryset.count() != 1 or not queryset[0].key_code:
            self.message_user(
                request,
                'Select exactly one prize that uses keys.',
                level=messages.ERROR,
            )
        else:
            return HttpResponseRedirect(
                reverse('admin:tracker_prize_key_import', args=(queryset[0].id,))
            )

    import_keys_action.short_description = 'Import Prize Keys'

    def set_state_accepted(self, request, queryset):
        mass_assign_action(self, request, queryset, 'state', 'ACCEPTED')

    set_state_accepted.short_description = 'Set state to Accepted'

    def set_state_pending(self, request, queryset):
        mass_assign_action(self, request, queryset, 'state', 'PENDING')

    set_state_pending.short_description = 'Set state to Pending'

    def set_state_denied(self, request, queryset):
        mass_assign_action(self, request, queryset, 'state', 'DENIED')

    set_state_denied.short_description = 'Set state to Denied'
    actions = [
        draw_prize_action,
        draw_prize_once_action,
        import_keys_action,
        set_state_accepted,
        set_state_pending,
        set_state_denied,
    ]

    def get_queryset(self, request):
        event = viewutil.get_selected_event(request)
        params = {}
        if not request.user.has_perm('tracker.can_edit_locked_events'):
            params['locked'] = False
        if event:
            params['event'] = event.id
        return filters.run_model_query('prize', params, user=request.user, mode='admin')

    def get_readonly_fields(self, request, obj=None):
        ret = list(self.readonly_fields)
        if obj and obj.key_code:
            ret.append('maxwinners')
            ret.append('maxmultiwin')
        return ret


class PrizeKeyImportForm(djforms.Form):
    keys = djforms.CharField(widget=djforms.Textarea)

    def clean_keys(self):
        keys = {k.strip() for k in self.cleaned_data['keys'].split('\n') if k.strip()}
        if tracker.models.PrizeKey.objects.filter(key__in=keys).exists():
            raise ValidationError('At least one key already exists.')
        return keys


@admin_auth(('tracker.change_prize', 'tracker.add_prize_key'))
def prize_key_import(request, prize):
    try:
        prize = tracker.models.Prize.objects.get(pk=prize)
    except tracker.models.Prize.DoesNotExist:
        raise Http404
    if not prize.key_code:
        messages.error(request, 'Cannot import prize keys to non key prizes.')
        return HttpResponseRedirect(reverse('admin:tracker_prize_changelist'))
    if prize.event.locked and not request.user.has_perm(
        'tracker.can_edit_locked_events'
    ):
        raise PermissionDenied
    form = PrizeKeyImportForm(data=request.POST if request.method == 'POST' else None)
    if form.is_valid():
        tracker.models.PrizeKey.objects.bulk_create(
            [
                tracker.models.PrizeKey(prize=prize, key=key)
                for key in form.cleaned_data['keys']
            ]
        )
        prize.save()
        count = len(form.cleaned_data['keys'])
        logutil.change(request, prize, 'Added %d key(s).' % count)
        messages.info(request, '%d key(s) added to prize.' % count)
        return HttpResponseRedirect(reverse('admin:tracker_prize_changelist'))
    return render(
        request,
        'admin/generic_form.html',
        {
            'title': 'Import keys for %s' % prize,
            'breadcrumbs': (
                (
                    reverse('admin:app_list', kwargs=dict(app_label='tracker')),
                    'Tracker',
                ),
                (reverse('admin:tracker_prize_changelist'), 'Prizes'),
                (reverse('admin:tracker_prize_change', args=(prize.id,)), prize),
                (None, 'Import Keys'),
            ),
            'form': form,
            'action': request.path,
        },
    )


class PrizeKeyAdmin(CustomModelAdmin):
    readonly_fields = (
        'prize',
        'prize_winner',
        'key',
    )  # don't allow editing of anything by default


class RunnerAdminForm(djforms.ModelForm):
    donor = make_ajax_field(tracker.models.Runner, 'donor', 'donor')

    class Meta:
        model = tracker.models.Runner
        exclude = ('', '')


class RunnerAdmin(CustomModelAdmin):
    form = RunnerAdminForm
    search_fields = [
        'name',
        'stream',
        'twitter',
        'youtube',
        'donor__alias',
        'donor__firstname',
        'donor__lastname',
        'donor__email',
    ]
    list_display = (
        'name',
        'stream',
        'twitter',
        'youtube',
        'donor',
    )
    fieldsets = [
        (None, {'fields': ('name', 'stream', 'twitter', 'youtube', 'donor',)}),
    ]


class SpeedRunAdminForm(djforms.ModelForm):
    event = make_ajax_field(
        tracker.models.SpeedRun, 'event', 'event', initial=latest_event_id
    )
    runners = make_ajax_field(tracker.models.SpeedRun, 'runners', 'runner')

    class Meta:
        model = tracker.models.SpeedRun
        exclude = ('', '')


class StartRunForm(djforms.Form):
    run_time = djforms.CharField(help_text='Run time of previous run')
    start_time = djforms.DateTimeField(help_text='Start time of current run')


def start_run_view(request, run):
    if not request.user.has_perm('tracker.change_speedrun'):
        raise PermissionDenied
    run = tracker.models.SpeedRun.objects.get(id=run)
    prev = tracker.models.SpeedRun.objects.filter(
        event=run.event, order__lt=run.order
    ).last()
    form = StartRunForm(
        data=request.POST if request.method == 'POST' else None,
        initial={'run_time': prev.run_time, 'start_time': run.starttime},
    )
    if form.is_valid():
        rt = tracker.models.event.TimestampField.time_string_to_int(
            form.cleaned_data['run_time']
        )
        endtime = prev.starttime + timedelta(milliseconds=rt)
        if form.cleaned_data['start_time'] < endtime:
            return HttpResponse(
                'Entered data would cause previous run to end after current run started',
                status=400,
                content_type='text/plain',
            )
        prev.run_time = form.cleaned_data['run_time']
        prev.setup_time = str(form.cleaned_data['start_time'] - endtime)
        prev.save()
        messages.info(request, 'Previous run time set to %s' % prev.run_time)
        messages.info(request, 'Previous setup time set to %s' % prev.setup_time)
        run.refresh_from_db()
        messages.info(request, 'Current start time is %s' % run.starttime)
        return HttpResponseRedirect(
            reverse('admin:tracker_speedrun_changelist') + '?event=%d' % run.event_id
        )
    return render(
        request,
        'admin/generic_form.html',
        dict(title='Set start time for %s' % run, form=form, action=request.path,),
    )


class SpeedRunAdmin(CustomModelAdmin):
    form = SpeedRunAdminForm
    search_fields = [
        'name',
        'description',
        'runners__name',
    ]
    list_filter = ['event', RunListFilter]
    inlines = [BidInline, PrizeInline]
    list_display = (
        'name',
        'category',
        'description',
        'deprecated_runners',
        'starttime',
        'run_time',
        'setup_time',
    )
    fieldsets = [
        (
            None,
            {
                'fields': (
                    'name',
                    'display_name',
                    'twitch_name',
                    'category',
                    'console',
                    'release_year',
                    'description',
                    'event',
                    'order',
                    'starttime',
                    'run_time',
                    'setup_time',
                    'deprecated_runners',
                    'runners',
                    'coop',
                    'tech_notes',
                )
            },
        ),
    ]
    readonly_fields = ('deprecated_runners', 'starttime')
    actions = ['start_run']

    def start_run(self, request, runs):
        if len(runs) != 1:
            self.message_user(request, 'Pick exactly one run.', level=messages.ERROR)
        elif not runs[0].order:
            self.message_user(request, 'Run has no order.', level=messages.ERROR)
        elif runs[0].order == 1:
            self.message_user(request, 'Run is first run.', level=messages.ERROR)
        else:
            return HttpResponseRedirect(reverse('admin:start_run', args=(runs[0].id,)))

    def get_queryset(self, request):
        event = viewutil.get_selected_event(request)
        params = {}
        if not request.user.has_perm('tracker.can_edit_locked_events'):
            params['locked'] = False
        if event:
            params['event'] = event.id
        return filters.run_model_query('run', params, user=request.user, mode='admin')


class LogAdminForm(djforms.ModelForm):
    event = make_ajax_field(
        tracker.models.Log, 'event', 'event', initial=latest_event_id
    )

    class Meta:
        model = tracker.models.Log
        exclude = ('', '')


class LogAdmin(CustomModelAdmin):
    form = LogAdminForm
    search_fields = ['category', 'message']
    date_hierarchy = 'timestamp'
    list_filter = [('timestamp', admin.DateFieldListFilter), 'event', 'user']
    readonly_fields = [
        'timestamp',
    ]
    fieldsets = [
        (None, {'fields': ['timestamp', 'category', 'event', 'user', 'message',]}),
    ]

    def get_queryset(self, request):
        event = viewutil.get_selected_event(request)
        params = {}
        if not request.user.has_perm('tracker.can_edit_locked_events'):
            params['locked'] = False
        if event:
            params['event'] = event.id
        return filters.run_model_query('log', params, user=request.user, mode='admin')

    def has_add_permission(self, request, obj=None):
        return self.has_log_edit_perms(request, obj)

    def has_change_permission(self, request, obj=None):
        return self.has_log_edit_perms(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self.has_log_edit_perms(request, obj)

    def has_log_edit_perms(self, request, obj=None):
        return request.user.has_perm('tracker.can_change_log') and (
            obj is None
            or obj.event is None
            or (
                request.user.has_perm('tracker.can_edit_locked_events')
                or not obj.event.locked
            )
        )


class AdminActionLogEntryFlagFilter(SimpleListFilter):
    title = 'Action Type'
    parameter_name = 'action_flag'

    def lookups(self, request, model_admin):
        return (
            (admin.models.ADDITION, 'Added'),
            (admin.models.CHANGE, 'Changed'),
            (admin.models.DELETION, 'Deleted'),
        )

    def queryset(self, request, queryset):
        if self.value() is not None:
            flag = int(self.value())
            return queryset.filter(action_flag=flag)
        else:
            return queryset


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


@admin_auth()
def select_event(request):
    current = viewutil.get_selected_event(request)
    if request.method == 'POST':
        form = forms.EventFilterForm(data=request.POST)
        if form.is_valid():
            viewutil.set_selected_event(request, form.cleaned_data['event'])
            return redirect('admin:index')
    else:
        form = forms.EventFilterForm(**{'event': current})
    return render(request, 'admin/select_event.html', {'form': form})


@admin_auth('tracker.change_bid')
def show_completed_bids(request):
    current = viewutil.get_selected_event(request)
    params = {'feed': 'completed'}
    if current:
        params['event'] = current.id
    bids = filters.run_model_query('bid', params, user=request.user, mode='admin')
    bidList = list(bids)
    if request.method == 'POST':
        for bid in bidList:
            bid.state = 'CLOSED'
            bid.save()
            logutil.change(request, bid, 'Closed {0}'.format(str(bid)))
        return render(request, 'admin/completed_bids_post.html', {'bids': bidList})
    return render(request, 'admin/completed_bids.html', {'bids': bidList})


@admin_auth(('tracker.change_donor', 'tracker.change_donation'))
def process_donations(request):
    current_event = viewutil.get_selected_event(request)
    user_can_approve = (
        current_event and current_event.use_one_step_screening
    ) or request.user.has_perm('tracker.send_to_reader')
    return render(
        request,
        'admin/process_donations.html',
        {
            'user_can_approve': user_can_approve,
            'currentEvent': current_event,
            'apiUrls': mark_safe(json.dumps(api_urls())),
        },
    )


def api_urls():
    return {
        'adminBaseURL': reverse('admin:app_list', kwargs={'app_label': 'tracker'}),
        'searchURL': reverse('tracker:api_v1:search'),
        'editURL': reverse('tracker:api_v1:edit'),
        'addURL': reverse('tracker:api_v1:add'),
        'deleteURL': reverse('tracker:api_v1:delete'),
    }


@admin_auth(('tracker.change_donor', 'tracker.change_donation'))
def read_donations(request):
    currentEvent = viewutil.get_selected_event(request)
    return render(
        request,
        'admin/read_donations.html',
        {'currentEvent': currentEvent, 'apiUrls': mark_safe(json.dumps(api_urls()))},
    )


@admin_auth('tracker.change_prize')
def process_prize_submissions(request):
    currentEvent = viewutil.get_selected_event(request)
    return render(
        request,
        'admin/process_prize_submissions.html',
        {'currentEvent': currentEvent, 'apiUrls': mark_safe(json.dumps(api_urls()))},
    )


@admin_auth('tracker.change_bid')
def process_pending_bids(request):
    currentEvent = viewutil.get_selected_event(request)
    return render(
        request,
        'admin/process_pending_bids.html',
        {'currentEvent': currentEvent, 'apiUrls': mark_safe(json.dumps(api_urls()))},
    )


@admin_auth('tracker.change_prizewinner')
def automail_prize_contributors(request):
    if not hasattr(settings, 'EMAIL_HOST'):
        return HttpResponse('Email not enabled on this server.')
    currentEvent = viewutil.get_selected_event(request)
    if currentEvent is None:
        return HttpResponse('Please select an event first')
    prizes = prizemail.prizes_with_submission_email_pending(currentEvent)
    if request.method == 'POST':
        form = forms.AutomailPrizeContributorsForm(prizes=prizes, data=request.POST)
        if form.is_valid():
            prizemail.automail_prize_contributors(
                currentEvent,
                form.cleaned_data['prizes'],
                form.cleaned_data['emailtemplate'],
                sender=form.cleaned_data['fromaddress'],
                replyTo=form.cleaned_data['replyaddress'],
            )
            viewutil.tracker_log(
                'prize',
                'Mailed prize contributors',
                event=currentEvent,
                user=request.user,
            )
            return render(
                request,
                'admin/automail_prize_contributors_post.html',
                {'prizes': form.cleaned_data['prizes']},
            )
    else:
        form = forms.AutomailPrizeContributorsForm(prizes=prizes)
    return render(
        request,
        'admin/automail_prize_contributors.html',
        {'form': form, 'currentEvent': currentEvent},
    )


@admin_auth(('tracker.add_prizewinner', 'tracker.change_prizewinner'))
def draw_prize_winners(request):
    currentEvent = viewutil.get_selected_event(request)
    params = {'feed': 'todraw'}
    if currentEvent is not None:
        params['event'] = currentEvent.id
    prizes = filters.run_model_query('prize', params, user=request.user, mode='admin')
    if request.method == 'POST':
        form = forms.DrawPrizeWinnersForm(prizes=prizes, data=request.POST)
        if form.is_valid():
            for prize in form.cleaned_data['prizes']:
                status = True
                while status and not prize.maxed_winners():
                    status, data = prizeutil.draw_prize(
                        prize, seed=form.cleaned_data['seed']
                    )
                    prize.error = data['error'] if not status else ''
                logutil.change(request, prize, 'Prize Drawing')
            return render(
                request,
                'admin/draw_prize_winners_post.html',
                {'prizes': form.cleaned_data['prizes']},
            )
    else:
        form = forms.DrawPrizeWinnersForm(prizes=prizes)
    return render(request, 'admin/draw_prize_winners.html', {'form': form})


@admin_auth('tracker.change_prizewinner')
def automail_prize_winners(request):
    if not hasattr(settings, 'EMAIL_HOST'):
        return HttpResponse('Email not enabled on this server.')
    currentEvent = viewutil.get_selected_event(request)
    if currentEvent is None:
        return HttpResponse('Please select an event first')
    prizewinners = prizemail.prize_winners_with_email_pending(currentEvent)
    if request.method == 'POST':
        form = forms.AutomailPrizeWinnersForm(
            prizewinners=prizewinners, data=request.POST
        )
        if form.is_valid():
            for prizeWinner in form.cleaned_data['prizewinners']:
                prizeWinner.acceptdeadline = form.cleaned_data['acceptdeadline']
                prizeWinner.save()
            prizemail.automail_prize_winners(
                currentEvent,
                form.cleaned_data['prizewinners'],
                form.cleaned_data['emailtemplate'],
                sender=form.cleaned_data['fromaddress'],
                replyTo=form.cleaned_data['replyaddress'],
            )
            viewutil.tracker_log(
                'prize',
                'Mailed prize winner notifications',
                event=currentEvent,
                user=request.user,
            )
            return render(
                request,
                'admin/automail_prize_winners_post.html',
                {'prizewinners': form.cleaned_data['prizewinners']},
            )
    else:
        form = forms.AutomailPrizeWinnersForm(prizewinners=prizewinners)
    return render(request, 'admin/automail_prize_winners.html', {'form': form})


@admin_auth('tracker.change_prizewinner')
def automail_prize_accept_notifications(request):
    if not hasattr(settings, 'EMAIL_HOST'):
        return HttpResponse('Email not enabled on this server.')
    currentEvent = viewutil.get_selected_event(request)
    if currentEvent is None:
        return HttpResponse('Please select an event first')
    prizewinners = prizemail.prizes_with_winner_accept_email_pending(currentEvent)
    if request.method == 'POST':
        form = forms.AutomailPrizeAcceptNotifyForm(
            prizewinners=prizewinners, data=request.POST
        )
        if form.is_valid():
            prizemail.automail_winner_accepted_prize(
                currentEvent,
                form.cleaned_data['prizewinners'],
                form.cleaned_data['emailtemplate'],
                sender=form.cleaned_data['fromaddress'],
                replyTo=form.cleaned_data['replyaddress'],
            )
            viewutil.tracker_log(
                'prize',
                'Mailed prize accept notifications',
                event=currentEvent,
                user=request.user,
            )
            return render(
                request,
                'admin/automail_prize_winners_accept_notifications_post.html',
                {'prizewinners': form.cleaned_data['prizewinners']},
            )
    else:
        form = forms.AutomailPrizeAcceptNotifyForm(prizewinners=prizewinners)
    return render(
        request,
        'admin/automail_prize_winners_accept_notifications.html',
        {'form': form},
    )


@admin_auth('tracker.change_prizewinner')
def automail_prize_shipping_notifications(request):
    if not hasattr(settings, 'EMAIL_HOST'):
        return HttpResponse('Email not enabled on this server.')
    currentEvent = viewutil.get_selected_event(request)
    if currentEvent is None:
        return HttpResponse('Please select an event first')
    prizewinners = prizemail.prizes_with_shipping_email_pending(currentEvent)
    if request.method == 'POST':
        form = forms.AutomailPrizeShippingNotifyForm(
            prizewinners=prizewinners, data=request.POST
        )
        if form.is_valid():
            prizemail.automail_shipping_email_notifications(
                currentEvent,
                form.cleaned_data['prizewinners'],
                form.cleaned_data['emailtemplate'],
                sender=form.cleaned_data['fromaddress'],
                replyTo=form.cleaned_data['replyaddress'],
            )
            viewutil.tracker_log(
                'prize',
                'Mailed prize shipping notifications',
                event=currentEvent,
                user=request.user,
            )
            return render(
                request,
                'admin/automail_prize_winners_shipping_notifications_post.html',
                {'prizewinners': form.cleaned_data['prizewinners']},
            )
    else:
        form = forms.AutomailPrizeShippingNotifyForm(prizewinners=prizewinners)
    return render(
        request,
        'admin/automail_prize_winners_shipping_notifications.html',
        {'form': form},
    )


# http://stackoverflow.com/questions/2223375/multiple-modeladmins-views-for-same-model-in-django-admin
# viewName - what to call the model in the admin
# model - the model to use
# modelAdmin - the model admin manager to use
def admin_register_surrogate_model(viewName, model, modelAdmin):
    class Meta:
        proxy = True
        app_label = model._meta.app_label

    attrs = {'__module__': '', 'Meta': Meta}
    newmodel = type(viewName, (model,), attrs)
    admin.site.register(newmodel, modelAdmin)
    return modelAdmin


# TODO: create a surrogate model for Donation with all of the default filters already set?


admin.site.register(tracker.models.Bid, BidAdmin)
admin.site.register(tracker.models.DonationBid, DonationBidAdmin)
admin.site.register(tracker.models.BidSuggestion, BidSuggestionAdmin)
admin.site.register(tracker.models.Donation, DonationAdmin)
admin.site.register(tracker.models.Donor, DonorAdmin)
admin.site.register(tracker.models.Event, EventAdmin)
admin.site.register(tracker.models.SpeedRun, SpeedRunAdmin)
admin.site.register(tracker.models.Runner, RunnerAdmin)
admin.site.register(tracker.models.PostbackURL, PostbackURLAdmin)
admin.site.register(tracker.models.Submission)
admin.site.register(tracker.models.Prize, PrizeAdmin)
admin.site.register(tracker.models.PrizeCategory)
admin.site.register(tracker.models.PrizeKey, PrizeKeyAdmin)
admin.site.register(tracker.models.PrizeWinner, PrizeWinnerAdmin)
admin.site.register(tracker.models.DonorPrizeEntry, DonorPrizeEntryAdmin)
admin.site.register(tracker.models.UserProfile)
admin.site.register(tracker.models.Log, LogAdmin)
admin.site.register(admin.models.LogEntry, AdminActionLogEntryAdmin)
admin.site.register(tracker.models.Country)
admin.site.register(tracker.models.CountryRegion, CountryRegionAdmin)
admin.site.register(tracker.models.WordFilter)
admin.site.register(tracker.models.AmountFilter)

old_get_urls = admin.site.get_urls


def get_urls():
    urls = old_get_urls()
    return [
        url('select_event', select_event, name='select_event'),
        url('merge_bids', merge_bids_view, name='merge_bids'),
        url('merge_donors', merge_donors_view, name='merge_donors'),
        url(r'start_run/(?P<run>\d+)', start_run_view, name='start_run'),
        url(
            'automail_prize_contributors',
            automail_prize_contributors,
            name='automail_prize_contributors',
        ),
        url('draw_prize_winners', draw_prize_winners, name='draw_prize_winners'),
        url(
            r'prize_key_import/(?P<prize>\d+)',
            prize_key_import,
            name='tracker_prize_key_import',
        ),
        url(
            'automail_prize_winners',
            automail_prize_winners,
            name='automail_prize_winners',
        ),
        url(
            'automail_prize_accept_notifications',
            automail_prize_accept_notifications,
            name='automail_prize_accept_notifications',
        ),
        url(
            'automail_prize_shipping_notifications',
            automail_prize_shipping_notifications,
            name='automail_prize_shipping_notifications',
        ),
        url('show_completed_bids', show_completed_bids, name='show_completed_bids'),
        url('process_donations', process_donations, name='process_donations'),
        url('read_donations', read_donations, name='read_donations'),
        url(
            'process_prize_submissions',
            process_prize_submissions,
            name='process_prize_submissions',
        ),
        url('process_pending_bids', process_pending_bids, name='process_pending_bids'),
        url(r'draw_prize/(?P<id>\d+)', views.draw_prize, name='draw_prize'),
    ] + urls


admin.site.get_urls = get_urls
admin.site.index_template = 'admin/tracker_admin.html'
admin.site.site_header = 'Donation Tracker'
