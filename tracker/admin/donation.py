import json
from datetime import datetime, timedelta

from django.conf import settings
from django.conf.urls import url
from django.contrib.admin import register
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse, path
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from tracker import search_filters, forms, logutil, viewutil, models
from .filters import DonationListFilter
from .forms import DonationForm, DonorForm
from .inlines import DonationBidInline
from .util import (
    CustomModelAdmin,
    mass_assign_action,
    api_urls,
)


@register(models.Donation)
class DonationAdmin(CustomModelAdmin):
    class Media:
        css = {'all': ('admin/donation.css',)}

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
                    (
                        'transactionstate',
                        'bidstate',
                        'readstate',
                        'commentstate',
                        'pinned',
                    ),
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

    def send_donation_postbacks(self, request, queryset):
        from tracker import tasks

        queryset = queryset.filter(transactionstate='COMPLETED')
        for donation in queryset:
            if getattr(settings, 'HAS_CELERY', False):
                tasks.post_donation_to_postbacks.delay(donation.id)
            else:
                tasks.post_donation_to_postbacks(donation.id)
        self.message_user(request, 'Sent %d postbacks.' % queryset.count())

    send_donation_postbacks.short_description = 'Send postbacks.'

    def get_list_display(self, request):
        ret = list(self.list_display)
        if not request.user.has_perm('tracker.delete_all_donations'):
            ret.remove('transactionstate')
        return ret

    def get_readonly_fields(self, request, obj=None):
        perm = request.user.has_perm('tracker.delete_all_donations')
        # TODO: super?
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
        params = {}
        if not request.user.has_perm('tracker.can_edit_locked_events'):
            params['locked'] = False
        if request.user.has_perm('tracker.view_pending_donation'):
            params['feed'] = 'all'
        return search_filters.run_model_query('donation', params, user=request.user)

    def get_urls(self):
        return super(DonationAdmin, self).get_urls() + [
            path(
                'process_donations',
                self.admin_site.admin_view(self.process_donations),
                name='process_donations',
            ),
            path(
                'process_donations/<slug:event>',
                self.admin_site.admin_view(self.process_donations),
                name='process_donations',
            ),
            path(
                'read_donations',
                self.admin_site.admin_view(self.read_donations),
                name='read_donations',
            ),
            path(
                'read_donations/<slug:event>',
                self.admin_site.admin_view(self.read_donations),
                name='read_donations',
            ),
        ]

    @staticmethod
    @permission_required(('tracker.change_donation',))
    def process_donations(request, event=None):
        event = viewutil.get_event(event)

        if not event.id:
            return render(
                request,
                'tracker/eventlist.html',
                {
                    'events': models.Event.objects.all(),
                    'pattern': 'admin:process_donations',
                    'subheading': 'Process Pending Bids',
                },
            )

        user_can_approve = (
            event and event.use_one_step_screening
        ) or request.user.has_perm('tracker.send_to_reader')
        user_can_edit_donors = request.user.has_perm('tracker.change_donor')
        return render(
            request,
            'admin/tracker/process_donations.html',
            {
                'user_can_approve': user_can_approve,
                'user_can_edit_donors': user_can_edit_donors,
                'currentEvent': event,
                'apiUrls': mark_safe(json.dumps(api_urls())),
            },
        )

    @staticmethod
    @permission_required(('tracker.change_donation',))
    def read_donations(request, event=None):
        event = viewutil.get_event(event)

        if not event.id:
            return render(
                request,
                'tracker/eventlist.html',
                {
                    'events': models.Event.objects.all(),
                    'pattern': 'admin:process_pending_bids',
                    'subheading': 'Process Pending Bids',
                },
            )
        user_can_edit_donors = request.user.has_perm('tracker.change_donor')
        return render(
            request,
            'admin/tracker/read_donations.html',
            {
                'user_can_edit_donors': user_can_edit_donors,
                'currentEvent': event,
                'apiUrls': mark_safe(json.dumps(api_urls())),
            },
        )

    actions = [
        set_readstate_ready,
        set_readstate_ignored,
        set_readstate_read,
        set_commentstate_approved,
        set_commentstate_denied,
        cleanup_orphaned_donations,
        send_donation_postbacks,
    ]

    def get_actions(self, request):
        actions = super(DonationAdmin, self).get_actions(request)
        if (
            not request.user.has_perm('tracker.delete_all_donations')
            and 'delete_selected' in actions
        ):
            del actions['delete_selected']
        return actions


@register(models.Donor)
class DonorAdmin(CustomModelAdmin):
    form = DonorForm
    search_fields = ('email', 'paypalemail', 'alias', 'firstname', 'lastname')
    list_filter = ('donation__event', 'visibility')
    readonly_fields = ('visible_name', 'donations', 'full_alias')
    list_display = ('__str__', 'visible_name', 'full_alias', 'visibility')
    fieldsets = [
        (
            None,
            {
                'fields': [
                    'email',
                    'alias',
                    'full_alias',
                    'firstname',
                    'lastname',
                    'visibility',
                    'visible_name',
                    'user',
                    'solicitemail',
                    'donations',
                ]
            },
        ),
        ('Donor Info', {'classes': ['collapse'], 'fields': ['paypalemail']}),
        (
            'Address Info',
            {
                'classes': ['collapse'],
                'fields': [
                    'addressname',
                    'addressstreet',
                    'addresscity',
                    'addressstate',
                    'addresscountry',
                    'addresszip',
                ],
            },
        ),
    ]

    def donations(self, instance):
        if instance.id is not None:
            return format_html(
                '<a href="{u}?donor={id}">View</a>',
                u=(reverse('admin:tracker_donation_changelist')),
                id=instance.id,
            )
        else:
            return 'Not Saved Yet'

    def get_urls(self):
        return super(DonorAdmin, self).get_urls() + [
            url(
                'merge_donors',
                self.admin_site.admin_view(self.merge_donors_view),
                name='merge_donors',
            ),
        ]

    @staticmethod
    @permission_required('tracker.change_donor')
    def merge_donors_view(request):
        if request.method == 'POST':
            objects = [int(x) for x in request.POST['objects'].split(',')]
            form = forms.MergeObjectsForm(
                model=models.Donor, objects=objects, data=request.POST
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
            form = forms.MergeObjectsForm(model=models.Donor, objects=objects)
        return render(request, 'admin/tracker/merge_donors.html', {'form': form})

    def merge_donors(self, request, queryset):
        donors = queryset
        return HttpResponseRedirect(
            reverse('admin:merge_donors')
            + '?objects='
            + ','.join(str(o.id) for o in donors)
        )

    merge_donors.short_description = 'Merge selected donors'
    actions = [merge_donors]
