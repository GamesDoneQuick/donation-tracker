from django.contrib import messages
from django.contrib.admin import register
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse, path
from django.utils.safestring import mark_safe

from tracker import search_filters, forms, logutil, models, viewutil
from .filters import BidListFilter, BidParentFilter
from .forms import DonationBidForm, BidForm
from .inlines import BidOptionInline, BidDependentsInline
from .util import CustomModelAdmin


@register(models.Bid)
class BidAdmin(CustomModelAdmin):
    form = BidForm
    list_display = (
        '__str__',
        'speedrun',
        'event',
        'istarget',
        'goal',
        'total',
        'description',
        'state',
        'biddependency',
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

    def get_queryset(self, request):
        params = {}
        if request.user.has_perm('tracker.view_hidden_bid'):
            params['feed'] = 'all'
        if not request.user.has_perm('tracker.can_edit_locked_events'):
            params['locked'] = False
        return search_filters.run_model_query('allbids', params, user=request.user)

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

    def bid_open_action(self, request, queryset):
        self.bid_set_state_action(request, queryset, 'OPENED')

    bid_open_action.short_description = 'Set Bids as OPENED'

    def bid_close_action(self, request, queryset):
        self.bid_set_state_action(request, queryset, 'CLOSED')

    bid_close_action.short_description = 'Set Bids as CLOSED'

    def bid_hidden_action(self, request, queryset):
        self.bid_set_state_action(request, queryset, 'HIDDEN')

    bid_hidden_action.short_description = 'Set Bids as HIDDEN'

    def bid_set_state_action(self, request, queryset, value, recursive=False):
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
            b.save()  # can't use queryset.update because that doesn't send the post_save signals
            logutil.change(request, b, ['state'])
        if total and not recursive:
            messages.success(request, '%d bid(s) changed to %s.' % (total, value))
        return total

    actions = [bid_open_action, bid_close_action, bid_hidden_action, merge_bids]

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
class DonationBidAdmin(CustomModelAdmin):
    form = DonationBidForm
    list_display = ('bid', 'donation', 'amount')
    list_filter = ('donation__transactionstate',)

    def get_queryset(self, request):
        params = {}
        if not request.user.has_perm('tracker.can_edit_locked_events'):
            params['locked'] = False
        return search_filters.run_model_query('donationbid', params, user=request.user)
