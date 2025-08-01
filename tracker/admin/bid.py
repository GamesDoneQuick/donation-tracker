from django.contrib import messages
from django.contrib.admin import display, register
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.safestring import mark_safe

from tracker import forms, logutil, models, search_filters, util, viewutil

from .filters import BidListFilter, BidParentFilter, RunEventListFilter
from .inlines import BidChainedInline, BidDependentsInline, BidOptionInline
from .util import CustomModelAdmin, DonationStatusMixin, EventArchivedMixin


@register(models.Bid)
class BidAdmin(EventArchivedMixin, CustomModelAdmin):
    autocomplete_fields = (
        'speedrun',
        'event',
        'biddependency',
    )
    list_display = (
        'name',
        'parent_name',
        'speedrun_name',
        'event',
        'istarget',
        'chain',
        'goal',
        'total_count',
        'description',
        'state',
    )
    list_display_links = ('name',)
    search_fields = (
        'name',
        'speedrun__name',
        'description',
        'shortdescription',
        'parent__name',
    )
    list_filter = (
        'event',
        RunEventListFilter,
        'state',
        'istarget',
        'allowuseroptions',
        BidParentFilter,
        BidListFilter,
    )
    readonly_fields = (
        'chain_goal',
        'chain_remaining',
        'parent',
        'effective_parent',
        'total',
    )

    @display(description='Parent')
    def parent_name(self, obj):
        return obj.parent and obj.parent.name

    @display(description='Run')
    def speedrun_name(self, obj):
        return obj.speedrun and util.ellipsify(obj.speedrun.name_with_category, 40)

    @display(description='Total (Count)')
    def total_count(self, obj):
        return f'{obj.total} ({obj.count})'

    def get_list_display(self, request):
        ret = list(super().get_list_display(request))
        if 'event__id__exact' in request.GET:
            ret = [d for d in ret if d != 'event']
        if 'run' in request.GET:
            ret = [d for d in ret if d != 'speedrun_name']
        return ret

    def get_search_results(self, request, queryset, search_term):
        parent_view = self.get_parent_view(request)
        if parent_view and parent_view[0] in ('donationbid', 'donation'):
            queryset = queryset.filter(istarget=True)
        return super().get_search_results(request, queryset, search_term)

    @display(description='Effective Parent')
    def effective_parent(self, obj):
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
        elif obj.id is None:
            return 'Not saved yet'
        else:
            return '-'

    def get_queryset(self, request):
        params = {'feed': 'all'}
        return search_filters.run_model_query(
            'allbids', params, user=request.user
        ).select_related('parent', 'speedrun', 'event')

    def get_inlines(self, request, obj):
        inlines = []
        if obj is not None:
            if obj.goal:
                inlines.append(BidDependentsInline)
            if obj.chain:
                inlines.append(BidChainedInline)
            elif not obj.istarget:
                inlines.append(BidOptionInline)
        return inlines

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.parent:
            if 'state' in form.base_fields:
                form.base_fields['state'].choices = [
                    (obj.parent.state, 'Inherit Parent State'),
                    ('PENDING', 'Pending'),
                    ('DENIED', 'Denied'),
                ]
        elif 'state' in form.base_fields:
            # this doesn't allow adding pending/denied children without going through the inline, but I struggle
            # to think of a use case for that either way
            form.base_fields['state'].choices = [
                c
                for c in form.base_fields['state'].choices
                if c[0] in models.Bid.TOP_LEVEL_STATES
            ]
        return form

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj and obj.parent:
            if not obj.parent.allowuseroptions:
                readonly_fields = readonly_fields + ('state',)
            if obj.chain:
                readonly_fields = readonly_fields + ('istarget',)
            readonly_fields = readonly_fields + (
                'event',
                'speedrun',
                'chain',
            )
        return readonly_fields

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (
                None,
                {
                    'fields': [
                        'name',
                        'state',
                        'description',
                        'shortdescription',
                        'estimate',
                        'close_at',
                        'post_run',
                        'goal',
                        'chain_goal',
                        'chain_remaining',
                        'total',
                        'repeat',
                        'istarget',
                        'chain',
                        'accepted_number',
                        'allowuseroptions',
                        'option_max_length',
                        'revealedtime',
                    ]
                },
            ),
            (
                'Link Info',
                {
                    'fields': [
                        'event',
                        'speedrun',
                        'parent',
                        'effective_parent',
                        'biddependency',
                    ]
                },
            ),
        ]
        if not (obj and obj.chain):
            fieldsets[0][1]['fields'].remove('chain_goal')
            fieldsets[0][1]['fields'].remove('chain_remaining')
        if obj and obj.parent:
            fieldsets[0][1]['fields'].remove('close_at')
            fieldsets[0][1]['fields'].remove('post_run')
        if obj and (obj.chain or obj.parent):
            fieldsets[0][1]['fields'].remove('accepted_number')
            fieldsets[0][1]['fields'].remove('repeat')
            fieldsets[0][1]['fields'].remove('allowuseroptions')
            fieldsets[0][1]['fields'].remove('option_max_length')
        return fieldsets

    def has_add_permission(self, request):
        return request.user.has_perm('tracker.top_level_bid')

    def has_delete_permission(self, request, obj=None):
        return super(BidAdmin, self).has_delete_permission(request, obj) and (
            obj is None
            or request.user.has_perm('tracker.delete_all_bids')
            or not obj.total
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

    def bid_open_action(self, request, queryset):
        self.bid_set_state_action(request, queryset, 'OPENED')

    bid_open_action.short_description = 'Set Bids as OPENED'

    def bid_close_action(self, request, queryset):
        self.bid_set_state_action(request, queryset, 'CLOSED')

    bid_close_action.short_description = 'Set Bids as CLOSED'

    def bid_hide_action(self, request, queryset):
        self.bid_set_state_action(request, queryset, 'HIDDEN')

    bid_hide_action.short_description = 'Set Bids as HIDDEN'

    def bid_set_state_action(self, request, queryset, value, recursive=False):
        unchanged = queryset.filter(event__archived=True)
        if unchanged.exists():
            messages.warning(
                request,
                f'{unchanged.count()} bid(s) unchanged due to the event being archived.',
            )
        queryset = queryset.filter(event__archived=False)
        if not recursive:
            unchanged = queryset.filter(level__gt=0)
            if unchanged.exists():
                messages.warning(
                    request,
                    f'{unchanged.count()} bid(s) possibly unchanged because you can only use the dropdown on top level bids.',
                )
            queryset = queryset.filter(level=0)
        total = queryset.count()
        for b in queryset:
            b.state = value
            b.save()  # can't use queryset.update because that doesn't send the post_save signals
            logutil.change(request, b, ['state'])
        if total and not recursive:
            messages.success(request, f'{total} bid(s) changed to {value}.')
        return total

    actions = [bid_open_action, bid_close_action, bid_hide_action, merge_bids]

    @staticmethod
    @permission_required('tracker.change_bid')
    def merge_bids_view(request, *args, **kwargs):
        if request.method == 'POST':
            objects = [int(x) for x in request.POST['objects'].split(',')]
            form = forms.MergeObjectsForm(
                model=models.Bid, objects=objects, data=request.POST
            )
            if form.is_valid():
                viewutil.merge_bids(
                    form.cleaned_data['root'], form.cleaned_data['objects']
                )
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
            form = forms.MergeObjectsForm(model=models.Bid, objects=objects)
        return render(request, 'admin/tracker/merge_bids.html', {'form': form})

    def get_urls(self):
        return super(BidAdmin, self).get_urls() + [
            path(
                'merge_bids',
                self.admin_site.admin_view(self.merge_bids_view),
                name='merge_bids',
            ),
        ]

    def get_actions(self, request):
        actions = super(BidAdmin, self).get_actions(request)
        if (
            not request.user.has_perm('tracker.delete_all_bids')
            and 'delete_selected' in actions
        ):
            del actions['delete_selected']
        return actions


@register(models.DonationBid)
class DonationBidAdmin(EventArchivedMixin, DonationStatusMixin, CustomModelAdmin):
    autocomplete_fields = ('bid',)
    list_display = (
        'bid',
        'event',
        'donation',
        'transactionstate',
        'testdonation',
        'amount',
    )
    list_filter = (
        'bid__event',
        'donation__transactionstate',
    )
    event_child_fields = (
        'bid',
        'donation',
    )
    readonly_fields = ('donation',)  # only allow adding via the donation's bid inline

    def get_queryset(self, request):
        queryset = (
            super().get_queryset(request).select_related('donation', 'donation__donor')
        )
        return queryset

    def get_event_filter_key(self):
        return 'bid__event'

    @display
    def transactionstate(self, obj):
        return obj.donation.transactionstate

    @display(boolean=True)
    def testdonation(self, obj):
        return obj.donation.testdonation

    # only allow adding via the donation's bid inline
    def has_add_permission(self, request):
        return False
