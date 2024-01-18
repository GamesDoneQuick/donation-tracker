from django.contrib import messages
from django.contrib.admin import display, register
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.safestring import mark_safe

from tracker import forms, logutil, models, search_filters, viewutil

from .filters import BidListFilter, BidParentFilter
from .forms import BidForm, DonationBidForm
from .inlines import BidChainedInline, BidDependentsInline, BidOptionInline
from .util import CustomModelAdmin, DonationStatusMixin, EventLockedMixin


@register(models.Bid)
class BidAdmin(EventLockedMixin, CustomModelAdmin):
    form = BidForm
    list_display = (
        '__str__',
        'speedrun',
        'event',
        'istarget',
        'chain',
        'goal',
        'total',
        'description',
        'state',
        'biddependency',
        'estimate',
        'close_at',
    )
    list_display_links = ('__str__',)
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
    readonly_fields = (
        'chain_goal',
        'chain_remaining',
        'parent',
        'effective_parent',
        'total',
    )

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
        params = {}
        if request.user.has_perm('tracker.view_hidden_bid'):
            params['feed'] = 'all'
        return search_filters.run_model_query('allbids', params, user=request.user)

    def get_inlines(self, request, obj):
        if obj is None:
            return []
        elif obj.chain:
            return [BidChainedInline, BidDependentsInline]
        else:
            return [BidOptionInline, BidDependentsInline]

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
                'pinned',
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
                        'pinned',
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
        if not request.user.has_perm('tracker.can_edit_locked_events'):
            unchanged = queryset.filter(event__locked=True)
            if unchanged.exists():
                messages.warning(
                    request,
                    f'{unchanged.count()} bid(s) unchanged due to the event being locked.',
                )
            queryset = queryset.filter(event__locked=False)
        if not recursive:
            unchanged = queryset.filter(parent__isnull=False)
            if unchanged.exists():
                messages.warning(
                    request,
                    f'{unchanged.count()} bid(s) possibly unchanged because you can only use the dropdown on top level bids.',
                )
            queryset = queryset.filter(parent__isnull=True)
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
class DonationBidAdmin(EventLockedMixin, DonationStatusMixin, CustomModelAdmin):
    form = DonationBidForm
    list_display = ('bid', 'donation', 'transactionstate', 'amount')
    list_filter = (
        'bid__event',
        'donation__transactionstate',
    )
    event_child_fields = (
        'bid',
        'donation',
    )
    readonly_fields = ('donation',)

    def get_queryset(self, request):
        queryset = (
            super().get_queryset(request).select_related('donation', 'donation__donor')
        )
        return queryset

    @display
    def transactionstate(self, obj):
        return obj.donation.transactionstate

    # add directly to donations
    def has_add_permission(self, request):
        return False
