from __future__ import annotations

import datetime
from itertools import groupby
from typing import Any, Collection, Iterable, Mapping, Optional, Sequence

import post_office.mail
import post_office.models
from django.contrib import admin, messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template import Context, Engine, Template
from django.urls import path, reverse
from django.utils.decorators import method_decorator

from tracker import forms, models, settings, util, viewutil

from ..util import build_public_url
from .filters import PrizeLifecycleFilter, PrizeListFilter
from .forms import PrizeKeyImportForm
from .inlines import PrizeWinnerInline
from .util import (
    CustomModelAdmin,
    EventArchivedMixin,
    RelatedUserMixin,
    mass_assign_action,
)


@admin.register(models.PrizeClaim)
class PrizeWinnerAdmin(EventArchivedMixin, CustomModelAdmin):
    autocomplete_fields = ('winner', 'prize')
    event_child_fields = ('prize',)
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
                    'winneremailsent',
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

    def get_event_filter_key(self):
        return 'prize__event'


@admin.register(models.DonorPrizeEntry)
class DonorPrizeEntryAdmin(EventArchivedMixin, CustomModelAdmin):
    autocomplete_fields = ('donor', 'prize')
    model = models.DonorPrizeEntry
    event_child_fields = ('prize',)
    search_fields = [
        'prize__name',
        'donor__email',
        'donor__alias',
        'donor__firstname',
        'donor__lastname',
    ]
    list_display = ['prize', 'donor']
    list_filter = ['prize__event']
    fieldsets = [
        (None, {'fields': ['donor', 'prize']}),
    ]


def _validate_template(
    template: post_office.models.EmailTemplate,
    template_context: Mapping[str, Any],
    possibly_unused: Optional[Iterable[str]] = None,
) -> Optional[HttpResponse]:
    engine = Engine(string_if_invalid='`__invalid_variable__: %s`')
    subject_template = Template(
        template.subject,
        engine=engine,
    )
    text_template = Template(
        template.content,
        engine=engine,
    )
    html_template = Template(
        template.html_content,
        engine=engine,
    )
    subject_used_variables = set()
    text_used_variables = set()
    html_used_variables = set()
    possibly_unused = set(possibly_unused or [])

    def subject_used(k):
        def _inner():
            subject_used_variables.add(k)
            return template_context[k]

        return _inner

    def text_used(k):
        def _inner():
            text_used_variables.add(k)
            return template_context[k]

        return _inner

    def html_used(k):
        def _inner():
            html_used_variables.add(k)
            return template_context[k]

        return _inner

    subject_result = subject_template.render(
        Context({k: subject_used(k) for k in template_context})
    )
    text_result = text_template.render(
        Context({k: text_used(k) for k in template_context})
    )
    html_result = html_template.render(
        Context({k: html_used(k) for k in template_context})
    )

    # special case for backwards compatibility
    if 'prize_wins' in possibly_unused:
        for used in [subject_used_variables, text_used_variables, html_used_variables]:
            if 'prize_wins' in used:
                used.add('claims')

    if (
        text_used_variables
        and html_used_variables
        and text_used_variables != html_used_variables
    ):
        return HttpResponse(
            f'Could not send email with that template, text and html used different variables:\n{", ".join(text_used_variables ^ html_used_variables)}',
            content_type='text/plain; charset=UTF-8',
            status=400,
        )

    used_variables = subject_used_variables | text_used_variables | html_used_variables

    if required := (set(template_context) - used_variables - possibly_unused):
        return HttpResponse(
            f'Could not send email with that template, the following variables were not used:\n{", ".join(required)}',
            content_type='text/plain; charset=UTF-8',
            status=400,
        )

    if (
        '__invalid_variable__' in subject_result
        or '__invalid_variable__' in text_result
        or '__invalid_variable__' in html_result
    ):
        return HttpResponse(
            f'Could not send email, template had at least one invalid lookup:\n\nSubject: {subject_result}\n\n{text_result}\n\n{html_result}',
            content_type='text/plain; charset=UTF-8',
            status=400,
        )
    else:
        return None


@admin.register(models.Prize)
class PrizeAdmin(EventArchivedMixin, RelatedUserMixin, CustomModelAdmin):
    autocomplete_fields = (
        'handler',
        'event',
        'startrun',
        'endrun',
        'allowed_prize_countries',
        'disallowed_prize_regions',
        'tags',
    )
    related_user_fields = ('handler',)
    list_display = (
        'name',
        'tags_',
        'minimumbid',
        'games',
        'start_draw_time',
        'end_draw_time',
        'sumdonations',
        'randomdraw',
        'event',
        'provider',
        'handler',
        'key_code',
        'lifecycle',
    )
    list_filter = ('event', 'state', PrizeListFilter, PrizeLifecycleFilter)
    fieldsets = [
        (
            None,
            {
                'fields': [
                    'name',
                    'description',
                    'shortdescription',
                    'tags',
                    'image',
                    'altimage',
                    'imagefile',
                    'event',
                    'requiresshipping',
                    'handler',
                    'handler_email',
                    'key_code',
                    'lifecycle',
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
                    'minimumbid',
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
        'tags__name',
    )
    inlines = [PrizeWinnerInline]
    readonly_fields = ('handler_email', 'lifecycle')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        if request.user.has_perm('tracker.view_prizeclaim'):
            queryset = queryset.time_annotation().claim_annotations()
        return queryset.prefetch_related('tags', 'claims__winner').select_related(
            'event',
            'startrun',
            'endrun',
            'handler',
            'prev_run',
            'next_run',
        )

    @admin.display(description='Tags')
    def tags_(self, obj):
        return ', '.join(t.name for t in obj.tags.all()) or None

    def handler_email(self, obj):
        return obj.handler.email

    def games(self, obj):
        if obj.startrun is None:
            return ''
        else:
            parts = [obj.startrun.name_with_category]
            if obj.startrun != obj.endrun:
                parts.append(obj.endrun.name_with_category)
            return ' <--> '.join(parts)

    def draw_prize_action(self, request, queryset):
        total_num_drawn = 0
        total_queued = 0
        for prize in queryset:
            from ..tasks import draw_prize

            if settings.TRACKER_HAS_CELERY:
                draw_prize.delay(prize.pk)
                total_queued += 1
            else:
                result, msg = draw_prize(prize)
                if not result:
                    self.message_user(request, msg['error'], level=messages.ERROR)
                else:
                    total_num_drawn += 1
        if total_num_drawn > 0:
            self.message_user(request, f'{total_num_drawn} prize(s) drawn.')
        if total_queued > 0:
            self.message_user(request, f'{total_queued} prize(s) queued for drawing.')

    draw_prize_action.short_description = 'Draw winner(s) for the selected prizes'

    def import_keys_action(self, request, queryset):
        queryset = queryset.filter(event__archived=False)
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
        import_keys_action,
        set_state_accepted,
        set_state_pending,
        set_state_denied,
    ]

    def get_list_display(self, request):
        list_display = list(super().get_list_display(request))
        if (
            not request.user.has_perm('tracker.view_prizeclaim')
            and 'lifecycle' in list_display
        ):
            list_display.remove('lifecycle')
        return list_display

    def get_list_filter(self, request):
        list_filter = list(super().get_list_filter(request))
        if not request.user.has_perm('tracker.view_prizeclaim') and (
            lifecycle := next(
                (
                    f
                    for f in list_filter
                    if getattr(f, 'parameter_name', None) == 'lifecycle'
                ),
                None,
            )
        ):
            list_filter.remove(lifecycle)
        return list_filter

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not request.user.has_perm('tracker.view_prizeclaim'):
            for s in fieldsets:
                if 'lifecycle' in s[1]['fields']:
                    s[1]['fields'].remove('lifecycle')
        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = tuple(super().get_readonly_fields(request, obj))
        if obj and obj.key_code:
            readonly_fields += ('maxwinners', 'requiresshipping')

        if not (
            request.user.has_perm('tracker.can_search_for_user')
            or request.user.has_perm('auth.view_user')
        ):
            readonly_fields += ('handler',)

        return readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None:
            if (e := form.base_fields['event'].initial) and (
                (pc := form.base_fields['event'].queryset.get(pk=e).prizecoordinator_id)
            ):
                form.base_fields['handler'].initial = pc
            form.base_fields['acceptemailsent'].initial = True
            form.base_fields['state'].initial = 'ACCEPTED'
        return form

    def get_inlines(self, request, obj):
        if obj is None:
            return []
        return super().get_inlines(request, obj)

    def add_view(self, request, form_url='', extra_context=None):
        """
        this is a weird wrinkle, but it's probably better to make it super obvious why adding a prize doesn't work
        rather than having people wondering why the add button isn't showing up (even if it's documented)
        """
        if not request.user.has_perm('tracker.can_search_for_user'):
            messages.error(
                request, 'Cannot add prize without `can_search_for_user` permission'
            )
            return HttpResponseRedirect(
                request.META.get(
                    'HTTP_REFERER', reverse('admin:tracker_prize_changelist')
                )
            )
        return super().add_view(request, form_url, extra_context)

    @method_decorator(
        permission_required(
            ('tracker.change_prize', 'tracker.add_prize_key'), raise_exception=True
        )
    )
    def prize_key_import(self, request, prize):
        try:
            prize = models.Prize.objects.get(pk=prize, event__archived=False)
        except models.Prize.DoesNotExist:
            raise Http404
        if not prize.key_code:
            messages.error(request, 'Cannot import prize keys to non key prizes.')
            return HttpResponseRedirect(reverse('admin:tracker_prize_changelist'))
        form = PrizeKeyImportForm(
            data=request.POST if request.method == 'POST' else None
        )
        if form.is_valid():
            models.PrizeKey.objects.bulk_create(
                [
                    models.PrizeKey(prize=prize, key=key)
                    for key in form.cleaned_data['keys']
                ]
            )
            prize.save()
            count = len(form.cleaned_data['keys'])
            self.log_change(request, prize, 'Added %d key(s).' % count)
            messages.info(request, '%d key(s) added to prize.' % count)
            return HttpResponseRedirect(reverse('admin:tracker_prize_changelist'))
        return render(
            request,
            'admin/tracker/generic_form.html',
            {
                'site_header': 'Donation Tracker',
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

    @staticmethod
    def _prize_mail_view_context(request, event, form, title):
        return {
            'site_header': 'Donation Tracker',
            'title': f'{title} for {event}',
            'breadcrumbs': (
                (
                    reverse('admin:app_list', kwargs=dict(app_label='tracker')),
                    'Tracker',
                ),
                (reverse('admin:tracker_event_changelist'), 'Events'),
                (reverse('admin:tracker_event_change', args=(event.id,)), event.name),
                (None, title),
            ),
            'form': form,
            'action': request.path,
        }

    @staticmethod
    def _prize_contributor_context(
        request: HttpRequest,
        event: models.Event,
        handler: AbstractUser,
        prizes: Iterable[models.Prize],
        reply_address: str,
        /,
    ):
        return {
            'user_index_url': build_public_url(reverse('tracker:user_index'), request),
            'event': event,
            'handler': handler,
            'accepted_prizes': [prize for prize in prizes if prize.state == 'ACCEPTED'],
            'denied_prizes': [prize for prize in prizes if prize.state == 'DENIED'],
            'reply_address': reply_address,
        }

    @method_decorator(permission_required('tracker.change_prize', raise_exception=True))
    def automail_prize_contributors(self, request, event=None):
        event = viewutil.get_event(event)

        if not event.id:
            return render(
                request,
                'tracker/eventlist.html',
                {
                    'events': models.Event.objects.all(),
                    'pattern': 'admin:tracker_automail_prize_contributors',
                    'subheading': 'Mail Prize Contributors',
                    'show_drafts': True,
                },
            )

        prizes = (
            models.Prize.objects.filter(event=event)
            .contributor_email_pending()
            .order_by('handler')
        )
        form = forms.AutomailPrizeContributorsForm(
            prizes, event, data=request.POST if request.method == 'POST' else None
        )
        if form.is_valid():
            prize = form.cleaned_data['prizes'].first()
            reply_address = form.cleaned_data['reply_address']

            if prize and (
                resp := _validate_template(
                    form.cleaned_data['email_template'],
                    PrizeAdmin._prize_contributor_context(
                        request, event, prize.handler, [prize], reply_address
                    ),
                )
            ):
                return resp

            for handler, handler_prizes in groupby(
                form.cleaned_data['prizes'].order_by('handler'),
                key=lambda p: p.handler,
            ):
                handler_prizes = list(handler_prizes)
                context = PrizeAdmin._prize_contributor_context(
                    request, event, handler, handler_prizes, reply_address
                )

                post_office.mail.send(
                    recipients=[handler.email],
                    sender=form.cleaned_data['from_address'],
                    template=form.cleaned_data['email_template'],
                    context=context,
                    headers={'Reply-to': form.cleaned_data['reply_address']},
                )

                self.message_user(
                    request,
                    f'Mailed prize handler {handler} for {len(handler_prizes)} prize(s)',
                )

                for prize in handler_prizes:
                    self.log_change(request, prize, 'Sent Accept/Deny email.')
                    prize.acceptemailsent = True
                    prize.save()
            return HttpResponseRedirect(reverse('admin:index'))
        return render(
            request,
            'admin/tracker/generic_form.html',
            PrizeAdmin._prize_mail_view_context(
                request, event, form, 'Mail Prize Contributors'
            ),
        )

    @method_decorator(permission_required('tracker.change_prize', raise_exception=True))
    def preview_prize_contributor_mail(self, request, prize, template):
        try:
            prize = (
                models.Prize.objects.contributor_email_pending()
                .select_related('event', 'handler')
                .get(pk=prize)
            )
            event = prize.event
            handler = prize.handler
            prizes = (
                models.Prize.objects.filter(event=event, handler=prize.handler)
                .contributor_email_pending()
                .select_related('event', 'handler')
            )
            template = post_office.models.EmailTemplate.objects.get(pk=template)
        except ObjectDoesNotExist:
            raise Http404
        format_context = PrizeAdmin._prize_contributor_context(
            request, event, handler, prizes, 'preview@example.com'
        )
        if resp := _validate_template(template, format_context):
            return resp
        mail = post_office.mail.create(
            'preview@example.com',
            template=template,
            context=format_context,
            commit=False,
        )
        return HttpResponse(
            f'Subject: {mail.subject}\n\n{mail.html_message}',
            content_type='text/plain; charset=UTF-8',
        )

    @staticmethod
    def _prize_winner_context(
        event: models.Event,
        winner: AbstractUser,
        claims: Collection[models.PrizeClaim],
        reply_address: str,
        accept_deadline: str | datetime.date | datetime.datetime,
        /,
    ):
        if isinstance(accept_deadline, datetime.datetime):
            accept_deadline = accept_deadline.date()
        return {
            'event': event,
            'winner': winner,
            'claims': claims,
            'requires_shipping': any(c for c in claims if c.requiresshipping),
            'reply_address': reply_address,
            'accept_deadline': accept_deadline,
            # deprecated
            'prize_wins': claims,
            'multi': len(claims) > 1,
            'prize_count': len(claims),
        }

    @method_decorator(
        permission_required(
            (
                'tracker.change_prizewinner',
                'tracker.view_donor',
                'tracker.change_prize',
            ),
            raise_exception=True,
        )
    )
    def automail_prize_winners(self, request, event=None):
        event = viewutil.get_event(event)

        if not event.id:
            return render(
                request,
                'tracker/eventlist.html',
                {
                    'events': models.Event.objects.all(),
                    'pattern': 'admin:tracker_automail_prize_winners',
                    'subheading': 'Mail Prize Winners',
                    'show_drafts': True,
                },
            )

        claims = (
            models.PrizeClaim.objects.filter(prize__event=event)
            .winner_email_pending()
            .order_by('winner_id')
        )
        form = forms.AutomailPrizeWinnersForm(
            claims, event, data=request.POST if request.method == 'POST' else None
        )
        if form.is_valid():
            claim = form.cleaned_data['claims'].first()
            accept_deadline = datetime.datetime.combine(
                form.cleaned_data['accept_deadline'],
                datetime.time(0, 0),
            ).replace(tzinfo=util.anywhere_on_earth_tz())

            if claim:
                claim.create_claim_url(request)

                if resp := _validate_template(
                    form.cleaned_data['email_template'],
                    PrizeAdmin._prize_winner_context(
                        event,
                        claim.winner,
                        [claim],
                        form.cleaned_data['reply_address'],
                        accept_deadline,
                    ),
                    {'prize_wins', 'multi', 'prize_count'},
                ):
                    return resp

            for winner, winner_claims in groupby(
                form.cleaned_data['claims'].order_by('winner_id'),
                lambda p: p.winner,
            ):
                winner_claims = list(winner_claims)

                for claim in winner_claims:
                    claim.create_claim_url(request)

                post_office.mail.send(
                    recipients=[claim.winner.email],
                    sender=form.cleaned_data['from_address'],
                    template=form.cleaned_data['email_template'],
                    context=PrizeAdmin._prize_winner_context(
                        event,
                        winner,
                        winner_claims,
                        form.cleaned_data['reply_address'],
                        accept_deadline,
                    ),
                    headers={'Reply-to': form.cleaned_data['reply_address']},
                )

                self.message_user(
                    request,
                    f'Mailed Donor {claim.winner.email} for {len(winner_claims)} won prize claim(s)',
                )

                for claim in winner_claims:
                    self.log_change(request, claim, 'Sent winner notification email.')
                    claim.winneremailsent = True
                    # "anywhere on earth" Time Zone is GMT-12
                    claim.acceptdeadline = accept_deadline
                    claim.save()
            return HttpResponseRedirect(reverse('admin:index'))
        return render(
            request,
            'admin/tracker/generic_form.html',
            PrizeAdmin._prize_mail_view_context(
                request, event, form, 'Mail Prize Winners'
            ),
        )

    @method_decorator(
        permission_required(
            (
                'tracker.change_prizewinner',
                'tracker.view_donor',
                'tracker.change_prize',
            ),
            raise_exception=True,
        )
    )
    def preview_prize_winner_mail(self, request, claim, template):
        try:
            claim = (
                models.PrizeClaim.objects.select_related('prize__event', 'winner')
                .winner_email_pending()
                .get(pk=claim)
            )
            event = claim.prize.event
            winner = claim.winner
            claims = models.PrizeClaim.objects.filter(
                prize__event=event, winner=winner
            ).winner_email_pending()
            template = post_office.models.EmailTemplate.objects.get(pk=template)
        except ObjectDoesNotExist:
            raise Http404
        for claim in claims:
            claim.create_claim_url(request)
        format_context = PrizeAdmin._prize_winner_context(
            event,
            winner,
            claims,
            'preview@example.com',
            claim.acceptdeadline or (util.utcnow() + datetime.timedelta(days=14)),
        )
        if resp := _validate_template(
            template, format_context, {'prize_wins', 'multi', 'prize_count'}
        ):
            return resp
        mail = post_office.mail.create(
            'preview@example.com',
            template=template,
            context=format_context,
            commit=False,
        )
        return HttpResponse(
            f'Subject: {mail.subject}\n\n{mail.html_message}',
            content_type='text/plain; charset=UTF-8',
        )

    @staticmethod
    def _prize_accept_context(
        request: HttpRequest,
        event: models.Event,
        handler: AbstractUser,
        claims: Sequence[models.PrizeClaim],
        reply_address: str,
        /,
    ):
        return {
            'event': event,
            'user_index_url': build_public_url(reverse('tracker:user_index'), request),
            'claims': claims,
            'handler': handler,
            'reply_address': reply_address,
            # deprecated
            'prize_wins': claims,
            'prize_count': len(claims),
        }

    @method_decorator(
        permission_required(
            ('tracker.change_prizewinner', 'tracker.change_prize'), raise_exception=True
        )
    )
    def automail_prize_accept_notifications(self, request, event=None):
        event = viewutil.get_event(event)

        if not event.id:
            return render(
                request,
                'tracker/eventlist.html',
                {
                    'events': models.Event.objects.all(),
                    'pattern': 'admin:tracker_automail_prize_accept_notifications',
                    'subheading': 'Mail Prize Accept Notifications',
                    'show_drafts': True,
                },
            )

        claims = (
            models.PrizeClaim.objects.filter(prize__event=event)
            .accept_email_pending()
            .order_by('prize__handler')
        )
        form = forms.AutomailPrizeAcceptNotifyForm(
            claims,
            event,
            data=request.POST if request.method == 'POST' else None,
        )
        if form.is_valid():
            claim = form.cleaned_data['claims'].first()

            if claim:
                if resp := _validate_template(
                    form.cleaned_data['email_template'],
                    PrizeAdmin._prize_accept_context(
                        request,
                        event,
                        claim.prize.handler,
                        [claim],
                        form.cleaned_data['reply_address'],
                    ),
                    {'prize_wins', 'event', 'prize_count'},
                ):
                    return resp

            for handler, handler_claims in groupby(
                form.cleaned_data['claims'].order_by('prize__handler'),
                lambda c: c.prize.handler,
            ):
                handler_claims = list(handler_claims)

                context = PrizeAdmin._prize_accept_context(
                    request,
                    event,
                    handler,
                    handler_claims,
                    form.cleaned_data['reply_address'],
                )

                post_office.mail.send(
                    recipients=[handler.email],
                    sender=form.cleaned_data['from_address'],
                    template=form.cleaned_data['email_template'],
                    context=context,
                    headers={'Reply-to': form.cleaned_data['reply_address']},
                )

                self.message_user(
                    request,
                    f'Mailed handler {handler} for {len(handler_claims)} accepted prize claim(s)',
                )

                for claim in handler_claims:
                    self.log_change(request, claim, 'Sent accepted claim email.')
                    claim.acceptemailsentcount = claim.acceptcount
                    claim.save()
            return HttpResponseRedirect(reverse('admin:index'))
        return render(
            request,
            'admin/tracker/generic_form.html',
            PrizeAdmin._prize_mail_view_context(
                request, event, form, 'Mail Prize Winners Accept Notifications'
            ),
        )

    @method_decorator(
        permission_required(
            ('tracker.change_prizewinner', 'tracker.change_prize'), raise_exception=True
        )
    )
    def preview_prize_accept_mail(self, request, claim, template):
        try:
            claim = (
                models.PrizeClaim.objects.select_related(
                    'prize__event', 'prize__handler'
                )
                .accept_email_pending()
                .get(pk=claim)
            )
            event = claim.prize.event
            handler = claim.prize.handler
            claims = (
                models.PrizeClaim.objects.filter(
                    prize__event=event, prize__handler=handler
                )
                .select_related('prize__event', 'prize__handler')
                .accept_email_pending()
            )
            template = post_office.models.EmailTemplate.objects.get(pk=template)
        except ObjectDoesNotExist:
            raise Http404
        for claim in claims:
            claim.create_claim_url(request)
        format_context = PrizeAdmin._prize_accept_context(
            request,
            event,
            handler,
            claims,
            'preview@example.com',
        )
        if resp := _validate_template(
            template, format_context, {'prize_wins', 'event', 'prize_count'}
        ):
            return resp
        mail = post_office.mail.create(
            'preview@example.com',
            template=template,
            context=format_context,
            commit=False,
        )
        return HttpResponse(
            f'Subject: {mail.subject}\n\n{mail.html_message}',
            content_type='text/plain; charset=UTF-8',
        )

    @staticmethod
    def _prize_shipped_context(
        event: models.Event,
        winner: models.Donor,
        claims: Sequence[models.PrizeClaim],
        reply_address: str,
        /,
    ):
        return {
            'event': event,
            'claims': claims,
            'winner': winner,
            'reply_address': reply_address,
            'shipped': any(c.requiresshipping for c in claims),
            'awarded': any(not c.requiresshipping for c in claims),
            # deprecated
            'prize_wins': claims,
            'prize_count': len(claims),
        }

    @method_decorator(
        permission_required(
            (
                'tracker.change_prizewinner',
                'tracker.view_donor',
                'tracker.change_prize',
            ),
            raise_exception=True,
        )
    )
    def automail_prize_shipping_notifications(self, request, event=None):
        event = viewutil.get_event(event)

        if not event.id:
            return render(
                request,
                'tracker/eventlist.html',
                {
                    'events': models.Event.objects.all(),
                    'pattern': 'admin:tracker_automail_prize_shipping_notifications',
                    'subheading': 'Mail Prize Shipping Notifications',
                    'show_drafts': True,
                },
            )

        claims = (
            models.PrizeClaim.objects.filter(prize__event=event)
            .shipped_email_pending()
            .order_by('winner_id')
        )
        form = forms.AutomailPrizeShippedForm(
            claims, event, data=request.POST if request.method == 'POST' else None
        )
        if form.is_valid():
            claim = form.cleaned_data['claims'].first()
            claim.create_claim_url(request)

            if claim and (
                resp := _validate_template(
                    form.cleaned_data['email_template'],
                    PrizeAdmin._prize_shipped_context(
                        event, claim.winner, [claim], form.cleaned_data['reply_address']
                    ),
                    {'prize_wins', 'prize_count', 'event', 'shipped', 'awarded'},
                )
            ):
                return resp

            for winner, winner_claims in groupby(
                form.cleaned_data['claims'].order_by('winner_id'), lambda c: c.winner
            ):
                winner_claims = list(winner_claims)
                for c in winner_claims:
                    c.create_claim_url(request)
                post_office.mail.send(
                    recipients=[winner.email],
                    sender=form.cleaned_data['from_address'],
                    template=form.cleaned_data['email_template'],
                    context=PrizeAdmin._prize_shipped_context(
                        event, winner, winner_claims, form.cleaned_data['reply_address']
                    ),
                    headers={'Reply-to': form.cleaned_data['reply_address']},
                )
                self.message_user(
                    request,
                    f'Mailed donor {winner.email} for {len(winner_claims)} shipped prize(s)',
                )
                for claim in winner_claims:
                    self.log_change(request, claim, 'Shipping email sent.')
                    claim.shippingemailsent = True
                    claim.save()
            return HttpResponseRedirect(reverse('admin:index'))
        return render(
            request,
            'admin/tracker/generic_form.html',
            PrizeAdmin._prize_mail_view_context(
                request, event, form, 'Mail Prize Winner Shipping Notifications'
            ),
        )

    @method_decorator(
        permission_required(
            (
                'tracker.change_prizewinner',
                'tracker.view_donor',
                'tracker.change_prize',
            ),
            raise_exception=True,
        )
    )
    def preview_prize_shipped_email(self, request, claim, template):
        try:
            claim = (
                models.PrizeClaim.objects.select_related('prize__event', 'winner')
                .shipped_email_pending()
                .get(pk=claim)
            )
            event = claim.prize.event
            winner = claim.winner
            claims = (
                models.PrizeClaim.objects.filter(prize__event=event, winner=winner)
                .select_related('prize__event', 'winner')
                .shipped_email_pending()
            )
            for c in claims:
                c.create_claim_url(request)
            template = post_office.models.EmailTemplate.objects.get(pk=template)
        except ObjectDoesNotExist:
            raise Http404
        format_context = PrizeAdmin._prize_shipped_context(
            event,
            winner,
            claims,
            'preview@example.com',
        )
        if resp := _validate_template(
            template, format_context, {'prize_wins', 'prize_count', 'event'}
        ):
            return resp
        mail = post_office.mail.create(
            'preview@example.com',
            template=template,
            context=format_context,
            commit=False,
        )
        return HttpResponse(
            f'Subject: {mail.subject}\n\n{mail.html_message}',
            content_type='text/plain; charset=UTF-8',
        )

    def get_urls(self):
        return super(PrizeAdmin, self).get_urls() + [
            path(
                'automail_prize_contributors',
                self.admin_site.admin_view(self.automail_prize_contributors),
                name='tracker_automail_prize_contributors',
            ),
            path(
                'automail_prize_contributors/<slug:event>',
                self.admin_site.admin_view(self.automail_prize_contributors),
                name='tracker_automail_prize_contributors',
            ),
            path(
                r'preview_prize_contributor_mail/<int:prize>/<int:template>',
                self.admin_site.admin_view(self.preview_prize_contributor_mail),
                name='tracker_preview_prize_contributor_mail',
            ),
            path(
                r'prize_key_import/<int:prize>',
                self.admin_site.admin_view(self.prize_key_import),
                name='tracker_prize_key_import',
            ),
            path(
                'automail_prize_winners',
                self.admin_site.admin_view(self.automail_prize_winners),
                name='tracker_automail_prize_winners',
            ),
            path(
                'automail_prize_winners/<slug:event>',
                self.admin_site.admin_view(self.automail_prize_winners),
                name='tracker_automail_prize_winners',
            ),
            path(
                r'preview_prize_winner_mail/<int:claim>/<int:template>',
                self.admin_site.admin_view(self.preview_prize_winner_mail),
                name='tracker_preview_prize_winner_mail',
            ),
            path(
                'automail_prize_accept_notifications',
                self.admin_site.admin_view(self.automail_prize_accept_notifications),
                name='tracker_automail_prize_accept_notifications',
            ),
            path(
                'automail_prize_accept_notifications/<slug:event>',
                self.admin_site.admin_view(self.automail_prize_accept_notifications),
                name='tracker_automail_prize_accept_notifications',
            ),
            path(
                r'preview_prize_accept_mail/<int:claim>/<int:template>',
                self.admin_site.admin_view(self.preview_prize_accept_mail),
                name='tracker_preview_prize_accept_mail',
            ),
            path(
                'automail_prize_shipping_notifications',
                self.admin_site.admin_view(self.automail_prize_shipping_notifications),
                name='tracker_automail_prize_shipping_notifications',
            ),
            path(
                'automail_prize_shipping_notifications/<slug:event>',
                self.admin_site.admin_view(self.automail_prize_shipping_notifications),
                name='tracker_automail_prize_shipping_notifications',
            ),
            path(
                r'preview_prize_shipping_mail/<int:claim>/<int:template>',
                self.admin_site.admin_view(self.preview_prize_shipped_email),
                name='tracker_preview_prize_shipped_mail',
            ),
        ]


@admin.register(models.PrizeKey)
class PrizeKeyAdmin(CustomModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    # these keys should be handled by the import script
