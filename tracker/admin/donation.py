import datetime

from django.contrib import messages
from django.contrib.admin import display, register
from django.contrib.auth.decorators import permission_required
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html

from tracker import forms, logutil, models, search_filters, settings, util, viewutil

from .filters import DonationListFilter
from .inlines import DonationBidInline
from .util import (
    CustomModelAdmin,
    EventLockedMixin,
    EventReadOnlyMixin,
    RelatedUserMixin,
    mass_assign_action,
)


@register(models.Donation)
class DonationAdmin(EventLockedMixin, CustomModelAdmin):
    autocomplete_fields = ['event', 'donor']
    list_display = (
        'id',
        'visible_donor_name',
        'amount',
        'comment',
        'timereceived',
        'event',
        'domain',
        'transactionstate',
        'readstate',
        'commentstate',
    )
    search_fields = (
        'donor__alias',
        'requestedalias',
        'amount',
        'comment',
        'modcomment',
    )
    list_filter = (
        'event',
        'transactionstate',
        'readstate',
        'commentstate',
        DonationListFilter,
    )
    readonly_fields = ['cleared_at', 'domainId', 'ipns_']
    inlines = (DonationBidInline,)

    def visible_donor_name(self, obj):
        if obj.donor:
            return obj.donor.visible_name()
        else:
            return None

    @display(description='PayPal IPNs')
    def ipns_(self, obj):
        return format_html(
            '<a href="{u}?donation={id}">View</a>',
            u=(
                reverse(
                    'admin:ipn_paypalipn_changelist',
                )
            ),
            id=obj.id,
        )

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
            timereceived__lte=util.utcnow() - datetime.timedelta(hours=8),
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
            if settings.TRACKER_HAS_CELERY:
                tasks.post_donation_to_postbacks.delay(donation.id)
            else:
                tasks.post_donation_to_postbacks(donation.id)
        self.message_user(request, 'Sent %d postbacks.' % queryset.count())

    send_donation_postbacks.short_description = 'Send postbacks.'

    def rescan_ipns(self, request, queryset):
        excluded = queryset.exclude(domain='PAYPAL')
        queryset = queryset.filter(domain='PAYPAL')
        from paypal.standard.ipn.models import PayPalIPN

        for d in queryset.filter():
            d.ipns.add(
                *PayPalIPN.objects.filter(
                    Q(custom__startswith=f'{d.id}:') | Q(txn_id=d.domainId)
                )
            )
        self.message_user(request, f'Scanned {queryset.count()} donations.')
        if excluded.count():
            self.message_user(
                request,
                f'Skipped {excluded.count()} non-PayPal donations.',
                level=messages.WARNING,
            )

    rescan_ipns.short_description = 'Rescan IPNs.'

    def get_list_display(self, request):
        list_display = list(super().get_list_display(request))
        if not request.user.has_perm('tracker.delete_all_donations'):
            list_display.remove('transactionstate')
        return tuple(list_display)

    def get_list_filter(self, request):
        list_filter = list(super().get_list_filter(request))
        if not request.user.has_perm('tracker.view_pending_donation'):
            list_filter.remove('transactionstate')
        return tuple(list_filter)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj:
            if 'commentstate' in form.base_fields:
                if obj.comment:
                    form.base_fields['commentstate'].choices = [
                        c
                        for c in form.base_fields['commentstate'].choices
                        if c[0] != 'ABSENT'
                    ]
            if 'readstate' in form.base_fields:
                if obj.event.use_one_step_screening:
                    form.base_fields['readstate'].choices = [
                        c
                        for c in form.base_fields['readstate'].choices
                        if c[0] != 'FLAGGED'
                    ]
                if (
                    not obj.user_can_send_to_reader(request.user)
                    and obj.readstate != 'READY'
                ):
                    form.base_fields['readstate'].choices = [
                        c
                        for c in form.base_fields['readstate'].choices
                        if c[0] != 'READY'
                    ]
        return form

    def get_readonly_fields(self, request, obj=None):
        perm = request.user.has_perm('tracker.delete_all_donations')
        readonly_fields = tuple(super().get_readonly_fields(request, obj))
        if not perm:
            readonly_fields += ('domain', 'fee', 'transactionstate', 'testdonation')
            if obj and obj.domain != 'LOCAL':
                readonly_fields += (
                    'donor',
                    'event',
                    'timereceived',
                    'amount',
                    'currency',
                )
        if not obj:
            readonly_fields += ('transactionstate', 'readstate', 'commentstate')
        elif obj.comment == '':
            readonly_fields += ('commentstate',)
        return readonly_fields

    def has_add_permission(self, request):
        return super().has_add_permission(request) and (
            request.user.has_perm('tracker.view_emails')
            and request.user.has_perm('tracker.view_full_names')
        )

    def has_delete_permission(self, request, obj=None):
        return super(DonationAdmin, self).has_delete_permission(request, obj) and (
            obj is None
            or obj.domain == 'LOCAL'
            or request.user.has_perm('tracker.delete_all_donations')
        )

    def get_search_fields(self, request):
        search_fields = tuple(super().get_search_fields(request))
        if request.user.has_perm('tracker.view_emails'):
            search_fields += ('donor__email', 'donor__paypalemail')
        if request.user.has_perm('tracker.view_full_names'):
            search_fields += ('donor__firstname', 'donor__lastname')
        return search_fields

    def get_queryset(self, request):
        params = {}
        if request.user.has_perm('tracker.view_pending_donation'):
            params['feed'] = 'all'
        return search_filters.run_model_query('donation', params, user=request.user)

    def get_fieldsets(self, request, obj=None):
        other_fields = ('domain', 'domainId')
        if (
            request.user.has_perm('ipn.view_paypalipn')
            and obj
            and obj.domain == 'PAYPAL'
        ):
            other_fields += ('ipns_',)

        fieldsets = [
            (None, {'fields': ('donor', 'event', 'timereceived', 'cleared_at')}),
            ('Comment State', {'fields': ('comment', 'modcomment')}),
            (
                'Donation State',
                {
                    'fields': (
                        (
                            'transactionstate',
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
            ('Other', {'fields': (other_fields,)}),
        ]

        return fieldsets

    actions = [
        set_readstate_ready,
        set_readstate_ignored,
        set_readstate_read,
        set_commentstate_approved,
        set_commentstate_denied,
        cleanup_orphaned_donations,
        send_donation_postbacks,
        rescan_ipns,
    ]

    def get_actions(self, request):
        if not self.has_change_permission(request):
            return {}
        actions = super(DonationAdmin, self).get_actions(request)
        if not request.user.has_perm('tracker.delete_all_donations'):
            actions.pop('delete_selected', None)
        if not self.has_delete_permission(request):
            actions.pop('cleanup_orphaned_donations', None)
        if not request.user.has_perm('ipn.view_paypalipn'):
            actions.pop('rescan_ipns', None)
        return actions

    def process_donations_view(self, request):
        event = models.Event.objects.current_or_next()
        if event is None:
            raise Http404
        return HttpResponseRedirect(
            reverse(
                'admin:tracker_ui',
                kwargs={'extra': f'v2/{event.pk}/processing/donations'},
            )
        )

    def read_donations_view(self, request):
        event = models.Event.objects.current_or_next()
        if event is None:
            raise Http404
        return HttpResponseRedirect(
            reverse(
                'admin:tracker_ui', kwargs={'extra': f'v2/{event.pk}/processing/read'}
            )
        )

    def get_urls(self):
        return super().get_urls() + [
            path(
                'process_donations',
                self.admin_site.admin_view(self.process_donations_view),
                name='process_donations',
            ),
            path(
                'read_donations',
                self.admin_site.admin_view(self.read_donations_view),
                name='read_donations',
            ),
        ]


@register(models.Donor)
class DonorAdmin(RelatedUserMixin, CustomModelAdmin):
    autocomplete_fields = ('user', 'addresscountry')
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

    def get_search_fields(self, request):
        search_fields = list(super().get_search_fields(request))
        if not request.user.has_perm('tracker.view_emails'):
            search_fields.remove('email')
            search_fields.remove('paypalemail')
        if not request.user.has_perm('tracker.view_full_names'):
            search_fields.remove('firstname')
            search_fields.remove('lastname')
        return tuple(search_fields)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = tuple(super().get_readonly_fields(request, obj))
        if not request.user.has_perm('tracker.can_search_for_user'):
            readonly_fields += ('user',)
        return readonly_fields

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
            path(
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


@register(models.Milestone)
class MilestoneAdmin(EventLockedMixin, EventReadOnlyMixin, CustomModelAdmin):
    autocomplete_fields = ('event', 'run')
    search_fields = ('name', 'description', 'short_description')
    list_filter = ('event',)
    list_display = ('name', 'event', 'start', 'amount', 'visible')
