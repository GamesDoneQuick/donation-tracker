import csv
import time
from collections import defaultdict
from decimal import Decimal
from io import BytesIO, StringIO
from urllib.parse import urlparse, urlunparse

from django import forms as djforms
from django.contrib import admin, messages
from django.contrib.admin import register
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.admin.utils import display_for_value
from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.contrib.auth import models as auth
from django.contrib.auth.decorators import permission_required, user_passes_test
from django.core.files.storage import DefaultStorage
from django.core.validators import EmailValidator
from django.db.models import Q, Sum
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_protect

import tracker.models.fields
from tracker import forms, logutil, models, search_filters, settings

from ..auth import send_registration_mail
from . import inlines
from .filters import EventFilter, RunListFilter, RunParticipantFilter
from .forms import StartRunForm, TestEmailForm
from .util import CustomModelAdmin, EventLockedMixin, RelatedUserMixin

# need to override the default behavior for this because the `view_user` permission is too broad


class UserAutocompleteView(AutocompleteJsonView):
    def get_queryset(self):
        queryset = auth.User.objects.all()
        if self.request.GET.get('term', None):
            queryset = queryset.filter(
                Q(username__icontains=self.request.GET['term'])
                | Q(email__icontains=self.request.GET['term'])
            )
        return queryset

    def has_perm(self, request, obj=None):
        return request.user.has_perm('tracker.can_search_for_user') or super().has_perm(
            request, obj
        )


@register(models.Event)
class EventAdmin(RelatedUserMixin, CustomModelAdmin):
    autocomplete_fields = (
        'prizecoordinator',
        'allowed_prize_countries',
        'disallowed_prize_regions',
    )
    related_user_fields = ('prizecoordinator',)
    search_fields = ('short', 'name')
    list_display = ['name', 'locked', 'allow_donations']
    list_editable = ['locked', 'allow_donations']
    readonly_fields = ['scheduleid', 'bids']
    fieldsets = [
        (
            None,
            {
                'fields': [
                    'short',
                    'name',
                    'hashtag',
                    'receivername',
                    'receiver_short',
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
            {
                'classes': ['collapse'],
                'fields': ['paypalemail', 'paypalcurrency', 'paypalimgurl'],
            },
        ),
        (
            'Donation Autoreply',
            {
                'classes': [
                    'collapse',
                ],
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
                'classes': [
                    # 'collapse',  # works around a bug(?) where the prizecoordinator field collapses to nothing
                ],
                'fields': [
                    'prize_accept_deadline_delta',
                    'prize_drawing_date',
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
        ('Bids', {'fields': ('bids',)}),
    ]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = tuple(super().get_readonly_fields(request, obj))
        if not request.user.has_perm('tracker.can_search_for_user'):
            readonly_fields += ('prizecoordinator',)
        return readonly_fields

    def get_search_results(self, request, queryset, search_term):
        parent_view = self.get_parent_view(request)
        if parent_view:
            queryset = queryset.exclude(locked=True)
        return super().get_search_results(request, queryset, search_term)

    def bids(self, instance):
        if instance.id is not None:
            return format_html(
                '<a href="{u}?event={id}">View</a>',
                u=(
                    reverse(
                        'admin:tracker_bid_changelist',
                    )
                ),
                id=instance.id,
            )
        else:
            return 'Not Saved Yet'

    def get_urls(self):
        return [
            path(
                'send_volunteer_emails/<int:pk>',
                self.admin_site.admin_view(self.send_volunteer_emails_view),
                name='send_volunteer_emails',
            ),
            path(
                'ui/',
                self.admin_site.admin_view(self.ui_view),
                name='tracker_ui',
            ),
            path(
                'ui/<path:extra>',
                self.admin_site.admin_view(self.ui_view),
                name='tracker_ui',
            ),
            path(
                'diagnostics',
                self.admin_site.admin_view(self.diagnostics),
                name='diagnostics',
            ),
            path(
                'total_watch',
                self.admin_site.admin_view(self.total_watch),
                name='total_watch',
            ),
            path(
                'user_autocomplete',
                self.admin_site.admin_view(
                    UserAutocompleteView.as_view(admin_site=self.admin_site)
                ),
                name='tracker_user_autocomplete',
            ),
        ] + super().get_urls()

    def send_volunteer_emails(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                'Select exactly one event.',
                level=messages.ERROR,
            )
            return
        return HttpResponseRedirect(
            reverse('admin:send_volunteer_emails', args=(queryset.first().id,))
        )

    @staticmethod
    @permission_required('auth.change_user', raise_exception=True)
    def send_volunteer_emails_view(request, pk):
        event = models.Event.objects.filter(pk=pk, locked=False).first()
        if event is None:
            raise Http404
        if request.method == 'POST':
            form = forms.SendVolunteerEmailsForm(request.POST, request.FILES)
            if form.is_valid():
                volunteers = csv.DictReader(
                    StringIO(request.FILES['volunteers'].read().decode('utf-8'))
                )
                tracker_group = auth.Group.objects.get_or_create(name='Bid Tracker')[0]
                tracker_codenames = [
                    'change_donation',
                    'view_donation',
                    'view_comments',
                    # bid assignment
                    'add_donationbid',
                    'change_donationbid',
                    'delete_donationbid',
                    'view_donationbid',
                    # milestones
                    'view_milestone',
                ]
                tracker_permissions = auth.Permission.objects.filter(
                    content_type__app_label='tracker',
                    codename__in=tracker_codenames,
                )
                assert tracker_permissions.count() == len(
                    tracker_codenames
                ), 'some permissions were missing, check tracker_codenames or that all migrations have run'

                tracker_group.permissions.set(tracker_permissions)
                admin_group = auth.Group.objects.get_or_create(name='Bid Admin')[0]
                admin_codenames = [
                    # bid assignment
                    'add_donationbid',
                    'change_donationbid',
                    'delete_donationbid',
                    'view_donationbid',
                    # bid screening/editing
                    'add_bid',
                    'change_bid',
                    'view_bid',
                    'top_level_bid',
                    # donations
                    'change_donation',
                    'view_donation',
                    'view_comments',
                    'view_pending_donation',
                    'send_to_reader',
                    # donors
                    'add_donor',
                    'change_donor',
                    'view_donor',
                    'view_emails',
                    'view_full_names',
                    # needed for 'Start Run'
                    'change_speedrun',
                    'view_speedrun',
                    'view_milestone',
                ]
                admin_permissions = auth.Permission.objects.filter(
                    content_type__app_label='tracker',
                    codename__in=admin_codenames,
                )
                assert admin_permissions.count() == len(
                    admin_codenames
                ), 'some permissions were missing, check admin_codenames or that all migrations have run'
                admin_group.permissions.set(admin_permissions)

                schedule_group = auth.Group.objects.get_or_create(
                    name='Schedule Viewer'
                )[0]
                schedule_codenames = [
                    'view_interstitial',
                ]
                schedule_permissions = auth.Permission.objects.filter(
                    content_type__app_label='tracker',
                    codename__in=schedule_codenames,
                )
                assert schedule_permissions.count() == len(
                    schedule_codenames
                ), 'some permissions were missing, check schedule_codenames or that all migrations have run'
                schedule_group.permissions.set(schedule_permissions)

                successful = 0
                email_validator = EmailValidator()
                for row, volunteer in enumerate(volunteers, start=2):
                    volunteer = defaultdict(str, volunteer)
                    try:
                        firstname, space, lastname = (
                            volunteer['name'].strip().partition(' ')
                        )
                        is_head = 'head' in volunteer['position'].strip().lower()
                        is_host = 'host' in volunteer['position'].strip().lower()
                        is_schedule = (
                            'schedule' in volunteer['position'].strip().lower()
                        )
                        email = volunteer['email'].strip()
                        email_validator(email)
                        username = volunteer['username'].strip()
                        if not username:
                            username = email
                        user, created = auth.User.objects.get_or_create(
                            email__iexact=volunteer['email'],
                            defaults=dict(
                                username=username,
                                first_name=firstname.strip(),
                                last_name=lastname.strip(),
                                email=email,
                                is_active=False,
                            ),
                        )
                        user.is_staff = True
                        if is_head:
                            user.groups.add(admin_group)
                            user.groups.remove(tracker_group)
                            user.groups.remove(schedule_group)
                        elif is_schedule:
                            user.groups.remove(admin_group)
                            user.groups.remove(tracker_group)
                            user.groups.add(schedule_group)
                        else:
                            user.groups.remove(admin_group)
                            user.groups.add(tracker_group)
                            user.groups.remove(schedule_group)
                        user.save()

                        if created:
                            messages.add_message(
                                request,
                                messages.INFO,
                                f'Created user {volunteer["username"]} with email {volunteer["email"]}',
                            )
                        else:
                            messages.add_message(
                                request,
                                messages.INFO,
                                f'Found existing user {user.username} with email {volunteer["email"]}',
                            )

                        context = dict(
                            event=event,
                            is_head=is_head,
                            is_host=is_host,
                            is_schedule=is_schedule,
                            password_reset_url=request.build_absolute_uri(
                                reverse('tracker:password_reset')
                            ),
                            admin_url=request.build_absolute_uri(
                                reverse('admin:index')
                            ),
                        )

                        send_registration_mail(
                            request,
                            user,
                            template=form.cleaned_data['template'],
                            sender=form.cleaned_data['sender'],
                            extra_context=context,
                        )
                        successful += 1
                    except Exception as e:
                        messages.add_message(
                            request,
                            messages.ERROR,
                            f'Could not process row #{row}: {repr(e)}',
                        )
                if successful:
                    messages.add_message(
                        request, messages.INFO, f'Sent {successful} email(s)'
                    )
                return redirect('admin:tracker_event_changelist')
        else:
            form = forms.SendVolunteerEmailsForm()
        return render(
            request,
            'admin/tracker/generic_form.html',
            {
                'form': form,
                'site_header': 'Send Volunteer Emails',
                'title': 'Send Volunteer Emails',
                'breadcrumbs': (
                    (
                        reverse('admin:app_list', kwargs=dict(app_label='tracker')),
                        'Tracker',
                    ),
                    (reverse('admin:tracker_event_changelist'), 'Events'),
                    (
                        reverse('admin:tracker_event_change', args=(event.id,)),
                        str(event),
                    ),
                    (None, 'Send Volunteer Emails'),
                ),
                'action': request.path,
            },
        )

    @staticmethod
    @csrf_protect
    @user_passes_test(lambda u: u.is_superuser)
    def diagnostics(request):
        from post_office import mail

        ping_socket_url = (
            request.build_absolute_uri(f'{reverse("tracker:index_all")}ws/ping/')
            .replace('https:', 'wss:')
            .replace('http:', 'ws:')
        )

        celery_socket_url = (
            request.build_absolute_uri(f'{reverse("tracker:index_all")}ws/celery/')
            .replace('https:', 'wss:')
            .replace('http:', 'ws:')
        )

        if request.method == 'POST':
            test_email_form = TestEmailForm(data=request.POST)
            if test_email_form.is_valid():
                mail.send(
                    [test_email_form.cleaned_data['email']],
                    f'webmaster@{request.get_host().split(":")[0]}',
                    subject='Test Email',
                    message='If you got this, email is set up correctly.',
                )
                messages.info(
                    request, 'Test email queued. Check Post Office models for status.'
                )
        else:
            test_email_form = TestEmailForm()

        try:
            storage = DefaultStorage()
            output = storage.save(f'testfile_{int(time.time())}', BytesIO(b'test file'))
            storage.open(output).read()
            assert storage.exists(output)
            storage.delete(output)
            storage_works = True
        except Exception as e:
            storage_works = e

        return render(
            request,
            'admin/tracker/diagnostics.html',
            {
                'is_secure': request.is_secure(),
                'test_email_form': test_email_form,
                'ping_socket_url': ping_socket_url,
                'celery_socket_url': celery_socket_url,
                'storage_works': storage_works,
                'TRACKER_HAS_CELERY': settings.TRACKER_HAS_CELERY,
            },
        )

    @staticmethod
    def ui_view(request, ROOT_PATH=None, TRACKER_PATH=None, extra='', **kwargs):
        ROOT_PATH = ROOT_PATH or reverse('admin:tracker_ui')
        TRACKER_PATH = TRACKER_PATH or reverse('tracker:index_all')
        if extra.startswith('v2'):
            template = 'ui/generated/processing.html'
        else:
            template = 'ui/generated/admin.html'

        from tracker.ui.views import constants

        return render(
            request,
            template,
            {
                'event': models.Event.objects.current(),
                'events': models.Event.objects.all(),
                'CONSTANTS': constants(request.user),
                'ROOT_PATH': ROOT_PATH,
                'TRACKER_PATH': TRACKER_PATH,
                'app_name': 'AdminApp',
                'form_errors': {},
                'props': {},
            },
        )

    @staticmethod
    def total_watch(request):
        event = models.Event.objects.current_or_next()
        if not event:
            raise Http404
        return HttpResponseRedirect(
            reverse('admin:tracker_ui', kwargs=({'extra': f'total_watch/{event.id}'}))
        )

    def donor_report(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                'Select exactly one event.',
                level=messages.ERROR,
            )
            return
        event = queryset.first()
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = (
            'attachment; filename="donor-report-%s.csv"' % event.short
        )
        writer = csv.writer(response)
        writer.writerow(['Name', 'Donation Sum', 'Donation Count'])
        anon = tracker.models.Donation.objects.filter(
            donor__visibility='ANON', transactionstate='COMPLETED', event=event
        )
        writer.writerow(
            [
                'All Anonymous Donations',
                anon.aggregate(Sum('amount'))['amount__sum'].quantize(Decimal('1.00')),
                anon.count(),
            ]
        )
        donors = (
            tracker.models.DonorCache.objects.filter(event=event)
            .exclude(donor__visibility='ANON')
            .select_related('donor')
            .iterator()
        )
        for d in donors:
            writer.writerow([d.visible_name(), d.donation_total, d.donation_count])
        return response

    donor_report.short_description = 'Export donor CSV'

    def run_report(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                'Select exactly one event.',
                level=messages.ERROR,
            )
            return
        event = queryset.first()
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = (
            'attachment; filename="run-report-%s.csv"' % event.short
        )
        writer = csv.writer(response)
        writer.writerow(
            ['Run', 'Event', 'Start Time', 'End Time', 'Runners', 'Runner Twitters']
        )
        runs = (
            tracker.models.SpeedRun.objects.filter(event=event)
            .exclude(order=None)
            .select_related('event')
            .prefetch_related('runners')
        )
        for r in runs:
            writer.writerow(
                [
                    str(r),
                    r.event.short,
                    r.starttime.astimezone(r.event.timezone).isoformat(),
                    r.endtime.astimezone(r.event.timezone).isoformat(),
                    ','.join(str(ru) for ru in r.runners.all()),
                    ','.join(ru.twitter for ru in r.runners.all() if ru.twitter),
                ]
            )
        return response

    run_report.short_description = 'Export run CSV'

    def donation_report(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                'Select exactly one event.',
                level=messages.ERROR,
            )
            return
        event = queryset.first()
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = (
            'attachment; filename="donation-report-%s.csv"' % event.short
        )
        writer = csv.writer(response)
        writer.writerow(['Donor', 'Event', 'Amount', 'Time Received'])
        donations = (
            tracker.models.Donation.objects.filter(
                transactionstate='COMPLETED', event=event
            )
            .select_related('donor', 'event')
            .iterator()
        )
        for d in donations:
            writer.writerow(
                [
                    d.donor.visible_name(),
                    d.event.short,
                    d.amount,
                    d.timereceived.astimezone(d.event.timezone).isoformat(),
                ]
            )
        return response

    donation_report.short_description = 'Export donation CSV'

    def bid_report(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                'Select exactly one event.',
                level=messages.ERROR,
            )
            return
        event = queryset.first()
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = (
            'attachment; filename="bid-report-%s.csv"' % event.short
        )
        writer = csv.writer(response)
        writer.writerow(['Id', 'Bid', 'Event', 'Target', 'Goal', 'Amount', 'Count'])
        bids = (
            tracker.models.Bid.objects.filter(
                state__in=['CLOSED', 'OPENED'], event=event
            )
            .order_by('event__datetime', 'speedrun__order', 'parent__name', '-total')
            .select_related('event', 'speedrun', 'parent')
            .iterator()
        )
        for b in bids:
            writer.writerow(
                [b.id, str(b), b.event.short, b.istarget, b.goal, b.total, b.count]
            )
        return response

    bid_report.short_description = 'Export bid CSV'

    def donationbid_report(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                'Select exactly one event.',
                level=messages.ERROR,
            )
            return
        event = queryset.first()
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = (
            'attachment; filename="donationbid-report-%s.csv"' % event.short
        )
        writer = csv.writer(response)
        writer.writerow(['Bid', 'Amount', 'Time'])
        donation_bids = (
            tracker.models.DonationBid.objects.filter(
                bid__state__in=['CLOSED', 'OPENED'],
                bid__event=event,
                donation__transactionstate='COMPLETED',
            )
            .order_by('donation__timereceived')
            .select_related('donation')
            .iterator()
        )
        for b in donation_bids:
            writer.writerow([b.bid_id, b.amount, b.donation.timereceived])
        return response

    donationbid_report.short_description = 'Export donation bid CSV'

    def prize_report(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                'Select exactly one event.',
                level=messages.ERROR,
            )
            return
        event = queryset.first()
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = (
            'attachment; filename="prize-report-%s.csv"' % event.short
        )
        writer = csv.writer(response)
        writer.writerow(
            [
                'Event',
                'Name',
                'Eligible Donors',
                'Exact Donors',
                'Start Time',
                'End Time',
            ]
        )
        prizes = tracker.models.Prize.objects.filter(
            state='ACCEPTED', event=event
        ).iterator()
        for p in prizes:
            eligible = p.eligible_donors()
            writer.writerow(
                [
                    p.event.short,
                    p.name,
                    len(eligible),
                    len([d for d in eligible if d['amount'] == p.minimumbid]),
                    p.start_draw_time(),
                    p.end_draw_time(),
                ]
            )
        return response

    prize_report.short_description = 'Export prize CSV'

    def email_report(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                'Select exactly one event.',
                level=messages.ERROR,
            )
            return
        event = queryset.first()
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = (
            'attachment; filename="email-report-%s.csv"' % event.short
        )
        writer = csv.writer(response)
        writer.writerow(['Email', 'Name', 'Anonymous', 'Donation Sum', 'Country'])
        donors = (
            tracker.models.DonorCache.objects.filter(
                event=event,
                donor__solicitemail='OPTIN',
            )
            .select_related('donor')
            .iterator()
        )
        for d in donors:
            if d.firstname:
                if d.lastname:
                    name = u'%s, %s' % (d.lastname, d.firstname)
                else:
                    name = d.firstname
            else:
                name = '(No Name Supplied)'
            writer.writerow(
                [
                    d.email,
                    name,
                    d.visibility == 'ANON',
                    d.donation_total,
                    d.addresscountry,
                ]
            )
        return response

    email_report.short_description = 'Export email opt-in CSV'

    actions = [
        send_volunteer_emails,
        donor_report,
        run_report,
        donation_report,
        bid_report,
        donationbid_report,
        prize_report,
        email_report,
    ]


@register(models.PostbackURL)
class PostbackURLAdmin(EventLockedMixin, CustomModelAdmin):
    autocomplete_fields = ('event',)
    search_fields = ('url',)
    list_filter = ('event',)
    list_display = ('url', 'event')
    fieldsets = [(None, {'fields': ['event', 'url']})]

    def get_readonly_fields(self, request, obj=None):
        return super().get_readonly_fields(request, obj)


@register(models.Talent)
class TalentAdmin(CustomModelAdmin):
    autocomplete_fields = ('donor',)
    search_fields = [
        'name',
        'stream',
        'twitter',
        'youtube',
        'platform',
        'pronouns',
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
        'platform',
        'pronouns',
        'donor',
    )
    readonly_fields = (
        'participating_',
        'runs_',
        'hosting_',
        'commentating_',
        'interviews_',
        'interviewer_',
        'subject_',
    )
    list_filter = [
        EventFilter(
            'participating',
            lambda v: (
                Q(runs__event=v) | Q(hosting__event=v) | Q(commentating__event=v)
            ),
            'Participating in Run by Event',
        ),
        EventFilter('runs'),
        EventFilter('hosting'),
        EventFilter('commentating'),
        EventFilter(
            'interviews',
            lambda v: (Q(interviewer_for__event=v) | Q(subject_for__event=v)),
            'Participating in Interview by Event',
        ),
        EventFilter('interviewer_for'),
        EventFilter('subject_for'),
    ]
    fieldsets = [
        (
            None,
            {
                'fields': (
                    'name',
                    'stream',
                    'twitter',
                    'youtube',
                    'platform',
                    'pronouns',
                    'donor',
                )
            },
        ),
        (
            'Participating',
            {
                'fields': (
                    'participating_',
                    'runs_',
                    'hosting_',
                    'commentating_',
                    'interviews_',
                    'interviewer_',
                    'subject_',
                )
            },
        ),
    ]

    @admin.display(description='Participating in Run')
    def participating_(self, instance):
        if instance.id is not None:
            return format_html(
                '<a href="{u}?participant={id}">View</a>',
                u=(
                    reverse(
                        'admin:tracker_speedrun_changelist',
                    )
                ),
                id=instance.id,
            )
        else:
            return 'Not Saved Yet'

    @admin.display(description='Runs')
    def runs_(self, instance):
        if instance.id is not None:
            return format_html(
                '<a href="{u}?runners={id}">View</a>',
                u=(
                    reverse(
                        'admin:tracker_speedrun_changelist',
                    )
                ),
                id=instance.id,
            )
        else:
            return 'Not Saved Yet'

    @admin.display(description='Hosting')
    def hosting_(self, instance):
        if instance.id is not None:
            return format_html(
                '<a href="{u}?hosts={id}">View</a>',
                u=(
                    reverse(
                        'admin:tracker_speedrun_changelist',
                    )
                ),
                id=instance.id,
            )
        else:
            return 'Not Saved Yet'

    @admin.display(description='Commentating')
    def commentating_(self, instance):
        if instance.id is not None:
            return format_html(
                '<a href="{u}?commentators={id}">View</a>',
                u=(
                    reverse(
                        'admin:tracker_speedrun_changelist',
                    )
                ),
                id=instance.id,
            )
        else:
            return 'Not Saved Yet'

    @admin.display(description='Participating in Interview')
    def interviews_(self, instance):
        if instance.id is not None:
            return format_html(
                '<a href="{u}?participant={id}">View</a>',
                u=(
                    reverse(
                        'admin:tracker_interview_changelist',
                    )
                ),
                id=instance.id,
            )
        else:
            return 'Not Saved Yet'

    @admin.display(description='Interviewer')
    def interviewer_(self, instance):
        if instance.id is not None:
            return format_html(
                '<a href="{u}?interviewers={id}">View</a>',
                u=(
                    reverse(
                        'admin:tracker_interview_changelist',
                    )
                ),
                id=instance.id,
            )
        else:
            return 'Not Saved Yet'

    @admin.display(description='Subject')
    def subject_(self, instance):
        if instance.id is not None:
            return format_html(
                '<a href="{u}?subjects={id}">View</a>',
                u=(
                    reverse(
                        'admin:tracker_interview_changelist',
                    )
                ),
                id=instance.id,
            )
        else:
            return 'Not Saved Yet'


@register(models.SpeedRun)
class SpeedRunAdmin(EventLockedMixin, CustomModelAdmin):
    autocomplete_fields = (
        'event',
        'runners',
        'hosts',
        'commentators',
        'priority_tag',
        'tags',
    )
    search_fields = [
        'name',
        'description',
        'runners__name',
        'hosts__name',
        'commentators__name',
        'priority_tag__name',
        'tags__name',
    ]
    list_filter = ['event', RunParticipantFilter, RunListFilter]
    list_display = (
        'name',
        'category',
        'tags_',
        'runners_',
        'hosts_',
        'commentators_',
        'start_time',
        'anchored',
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
                    'anchor_time',
                    'run_time',
                    'setup_time',
                    'runners',
                    'hosts',
                    'commentators',
                    'coop',
                    'onsite',
                    'tech_notes',
                    'layout',
                    'priority_tag',
                    'tags',
                )
            },
        ),
        ('Bids', {'fields': ('bids',)}),
    ]
    readonly_fields = ('starttime', 'bids')
    actions = ['start_run']
    inlines = (inlines.VideoLinkInline,)

    class Form(djforms.ModelForm):
        def clean(self):
            # duplicated logic because the model is saved before save_related() can be called, so we need to ensure that
            #  the form itself includes the priority_tag so that the tags list ends up correct in the end
            cleaned_data = super().clean()
            if cleaned_data['priority_tag']:
                cleaned_data['tags'] |= models.Tag.objects.filter(
                    id=cleaned_data['priority_tag'].id
                )
            return cleaned_data

    form = Form

    @admin.display(description='Tags')
    def tags_(self, instance):
        return ', '.join(str(t) for t in instance.tags.all()) or None

    @admin.display(description='Runners')
    def runners_(self, instance):
        return ', '.join(str(r) for r in instance.runners.all()) or None

    @admin.display(description='Hosts')
    def hosts_(self, instance):
        return ', '.join(str(h) for h in instance.hosts.all()) or None

    @admin.display(description='Commentators')
    def commentators_(self, instance):
        return ', '.join(str(c) for c in instance.commentators.all()) or None

    @admin.display(description='Start Time')
    def start_time(self, instance):
        if instance.order:
            if instance.order > 1:
                url = reverse('admin:start_run', args=(instance.id,))
                return mark_safe(
                    f'<a href="{url}">{display_for_value(instance.starttime, self.get_empty_value_display())}</a>'
                )
            else:
                return instance.starttime
        else:
            return None

    @admin.display(description='Anchored', boolean=True)
    def anchored(self, instance):
        return instance.anchor_time is not None

    def bids(self, instance):
        if instance.id is not None:
            return format_html(
                '<a href="{u}?speedrun={id}">View</a>',
                u=(
                    reverse(
                        'admin:tracker_bid_changelist',
                    )
                ),
                id=instance.id,
            )
        else:
            return 'Not Saved Yet'

    def start_run(self, request, runs):
        if len(runs) != 1:
            self.message_user(request, 'Pick exactly one run.', level=messages.ERROR)
        elif runs[0].event.locked:
            self.message_user(request, 'Run event is locked.', level=messages.ERROR)
        elif not runs[0].order:
            self.message_user(request, 'Run has no order.', level=messages.ERROR)
        else:
            prev = models.SpeedRun.objects.filter(
                event=runs[0].event_id, order__lt=runs[0].order
            ).last()

            if not prev:
                self.message_user(request, 'Run is first run.', level=messages.ERROR)
            else:
                form_url = reverse('admin:start_run', args=(runs[0].id,))
                preserved_filters = self.get_preserved_filters(request)
                form_url = add_preserved_filters(
                    {'preserved_filters': preserved_filters, 'opts': self.opts},
                    form_url,
                )
                return HttpResponseRedirect(form_url)

    @staticmethod
    @permission_required('tracker.change_speedrun')
    def start_run_view(request, run):
        extra = {}
        if '_changelist_filters' in request.GET:
            extra['_changelist_filters'] = request.GET.get('_changelist_filters')
        elif (referer := request.META.get('HTTP_REFERER', None)) and (
            qs := urlparse(referer)[4]
        ):
            extra['_changelist_filters'] = qs
        run = models.SpeedRun.objects.filter(id=run, event__locked=False).first()
        if not run:
            raise Http404
        prev = models.SpeedRun.objects.filter(
            event=run.event, order__lt=run.order
        ).last()
        anchored_run = (
            models.SpeedRun.objects.filter(event=run.event, order__gt=run.order)
            .exclude(anchor_time=None)
            .first()
        )
        checkpoint = (
            models.SpeedRun.objects.filter(
                event=run.event, order__lt=anchored_run.order
            ).last()
            if anchored_run
            else None
        )
        if not prev:
            raise Http404
        form = StartRunForm(
            data=request.POST if request.method == 'POST' else None,
            initial={
                'run_time': prev.run_time,
                'start_time': run.starttime,
                'run_id': run.id,
                'next_anchored_run': anchored_run.anchor_time if anchored_run else None,
                'checkpoint_available': checkpoint.setup_time if checkpoint else None,
            },
        )
        if form.is_valid():
            post_url = reverse('admin:tracker_speedrun_changelist')
            if preserved_filters := request.POST.get('_changelist_filters'):
                pieces = list(urlparse(post_url))
                pieces[4] = preserved_filters
                post_url = urlunparse(pieces)
            form.save()
            prev.refresh_from_db()
            logutil.change(
                request,
                prev,
                f'Set run time to {prev.run_time}. Set setup time to {prev.setup_time}.',
            )
            messages.info(request, 'Previous run time set to %s' % prev.run_time)
            messages.info(request, 'Previous setup time set to %s' % prev.setup_time)
            run.refresh_from_db()
            if run.anchor_time:
                logutil.change(request, run, f'Set anchor time to {run.anchor_time}.')
            messages.info(request, 'Current start time is %s' % run.starttime)
            return HttpResponseRedirect(post_url)
        return render(
            request,
            'admin/tracker/generic_form.html',
            {
                'site_header': 'Donation Tracker',
                'title': 'Set start time for %s' % run.name,
                'breadcrumbs': (
                    (
                        reverse('admin:app_list', kwargs=dict(app_label='tracker')),
                        'Tracker',
                    ),
                    (reverse('admin:tracker_speedrun_changelist'), 'Speedruns'),
                    (None, 'Start Run'),
                ),
                'form': form,
                'extra': extra,
                'action': request.path,
            },
        )

    def get_queryset(self, request):
        params = {}
        return (
            search_filters.run_model_query('run', params, user=request.user)
            .select_related('priority_tag')
            .prefetch_related('runners', 'hosts', 'commentators', 'tags')
        )

    def get_urls(self):
        return super(SpeedRunAdmin, self).get_urls() + [
            path(
                'start_run/<int:run>',
                self.admin_site.admin_view(self.start_run_view),
                name='start_run',
            ),
        ]


@admin.register(models.VideoLink)
class VideoLinkAdmin(EventLockedMixin, CustomModelAdmin):
    autocomplete_fields = ('run',)
    event_child_fields = ('run',)


@admin.register(models.Tag)
class TagAdmin(CustomModelAdmin):
    search_fields = ('name',)
