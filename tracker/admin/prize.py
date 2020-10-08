import datetime
import json
from itertools import groupby

import pytz
from django.conf import settings
from django.conf.urls import url
from django.contrib import messages
from django.contrib.admin import register
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.safestring import mark_safe

from tracker import (
    search_filters,
    forms,
    logutil,
    prizemail,
    prizeutil,
    viewutil,
    models,
)
from .filters import PrizeListFilter
from .forms import PrizeWinnerForm, DonorPrizeEntryForm, PrizeForm, PrizeKeyImportForm
from .inlines import PrizeWinnerInline
from .util import (
    CustomModelAdmin,
    mass_assign_action,
    api_urls,
)


@register(models.PrizeWinner)
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
        return search_filters.run_model_query('prizewinner', params, user=request.user)


@register(models.DonorPrizeEntry)
class DonorPrizeEntryAdmin(CustomModelAdmin):
    form = DonorPrizeEntryForm
    model = models.DonorPrizeEntry
    search_fields = [
        'prize__name',
        'donor__email',
        'donor__alias',
        'donor__firstname',
        'donor__lastname',
    ]
    list_display = ['prize', 'donor', 'weight']
    list_filter = ['prize__event']
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
        return search_filters.run_model_query('prizeentry', params, user=request.user)


@register(models.Prize)
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
                    'imagefile',
                    'event',
                    'category',
                    'requiresshipping',
                    'handler',
                    'handler_email',
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
    readonly_fields = ('handler_email', 'maximumbid')

    def handler_email(self, obj):
        return obj.handler.email

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

    def draw_prize_action(self, request, queryset):
        total_num_drawn = 0
        for prize in queryset:
            if prize.key_code:
                drawn, msg = prizeutil.draw_keys(prize)
                if drawn:
                    total_num_drawn += len(msg['winners'])
                else:
                    messages.error(request, msg['error'])
            else:
                num_to_draw = prize.maxwinners - prize.current_win_count()
                drawing_error = False
                num_drawn = 0
                while not drawing_error and num_drawn < num_to_draw:
                    drawn, msg = prizeutil.draw_prize(prize)
                    if not drawn:
                        self.message_user(request, msg['error'], level=messages.ERROR)
                        drawing_error = True
                    else:
                        num_drawn += 1
                total_num_drawn += num_drawn
        if total_num_drawn > 0:
            self.message_user(request, '%d prizes drawn.' % total_num_drawn)

    draw_prize_action.short_description = 'Draw winner(s) for the selected prizes'

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
        import_keys_action,
        set_state_accepted,
        set_state_pending,
        set_state_denied,
    ]

    def get_queryset(self, request):
        event = viewutil.get_selected_event(request)
        params = {'feed': 'all'}
        if not request.user.has_perm('tracker.can_edit_locked_events'):
            params['locked'] = False
        if event:
            params['event'] = event.id
        return search_filters.run_model_query('prize', params, user=request.user)

    def get_readonly_fields(self, request, obj=None):
        ret = list(self.readonly_fields)
        if obj and obj.key_code:
            ret.append('maxwinners')
            ret.append('maxmultiwin')
        return ret

    @staticmethod
    @permission_required(('tracker.change_prize', 'tracker.add_prize_key'))
    def prize_key_import(request, prize):
        try:
            prize = models.Prize.objects.get(pk=prize)
        except models.Prize.DoesNotExist:
            raise Http404
        if not prize.key_code:
            messages.error(request, 'Cannot import prize keys to non key prizes.')
            return HttpResponseRedirect(reverse('admin:tracker_prize_changelist'))
        if prize.event.locked and not request.user.has_perm(
            'tracker.can_edit_locked_events'
        ):
            raise PermissionDenied
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
            logutil.change(request, prize, 'Added %d key(s).' % count)
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
    @permission_required('tracker.change_prizewinner')
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
                    'admin/tracker/automail_prize_contributors_post.html',
                    {'prizes': form.cleaned_data['prizes']},
                )
        else:
            form = forms.AutomailPrizeContributorsForm(prizes=prizes)
        return render(
            request,
            'admin/tracker/automail_prize_contributors.html',
            {'form': form, 'currentEvent': currentEvent},
        )

    @staticmethod
    @permission_required(('tracker.add_prizewinner', 'tracker.change_prizewinner'))
    def draw_prize_winners(request):
        currentEvent = viewutil.get_selected_event(request)
        params = {'feed': 'todraw'}
        if currentEvent is not None:
            params['event'] = currentEvent.id
        prizes = search_filters.run_model_query('prize', params, user=request.user)
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
                    'admin/tracker/draw_prize_winners_post.html',
                    {'prizes': form.cleaned_data['prizes']},
                )
        else:
            form = forms.DrawPrizeWinnersForm(prizes=prizes)
        return render(request, 'admin/tracker/draw_prize_winners.html', {'form': form})

    @staticmethod
    @permission_required('tracker.change_prizewinner')
    def automail_prize_winners(request):
        if not hasattr(settings, 'EMAIL_HOST'):
            return HttpResponse('Email not enabled on this server.')
        current_event = viewutil.get_selected_event(request)
        if current_event is None:
            return HttpResponse('Please select an event first')

        import post_office.mail

        prizewinners = prizemail.prize_winners_with_email_pending(current_event)
        if request.method == 'POST':
            form = forms.AutomailPrizeWinnersForm(
                prizewinners=prizewinners, data=request.POST
            )
            if form.is_valid():
                for winner, prizewins in groupby(
                    sorted(
                        form.cleaned_data['prizewinners'], key=lambda p: p.winner.id
                    ),
                    lambda p: p.winner,
                ):
                    prizewins = list(prizewins)

                    for prizewin in prizewins:
                        prizewin.create_claim_url(request)

                    format_context = {
                        'event': current_event,
                        'winner': winner,
                        'prize_wins': prizewins,
                        'multi': len(prizewins) > 1,
                        'prize_count': len(prizewins),
                        'reply_address': form.cleaned_data['replyaddress'],
                        'accept_deadline': form.cleaned_data['acceptdeadline'],
                    }

                    post_office.mail.send(
                        recipients=[winner.email],
                        sender=form.cleaned_data['fromaddress'],
                        template=form.cleaned_data['emailtemplate'],
                        context=format_context,
                        headers={'Reply-to': form.cleaned_data['replyaddress']},
                    )

                    for prizewin in prizewins:
                        prizewin.emailsent = True
                        # "anywhere on earth" Time Zone is GMT-12
                        prizewin.acceptdeadline = datetime.datetime.combine(
                            form.cleaned_data['acceptdeadline']
                            + datetime.timedelta(days=1),
                            datetime.time(0, 0),
                        ).replace(tzinfo=pytz.timezone('Etc/GMT-12'))
                        prizewin.save()

                viewutil.tracker_log(
                    'prize',
                    'Mailed prize winner notifications',
                    event=current_event,
                    user=request.user,
                )
                return render(
                    request,
                    'admin/tracker/automail_prize_winners_post.html',
                    {'prizewinners': form.cleaned_data['prizewinners']},
                )
        else:
            form = forms.AutomailPrizeWinnersForm(prizewinners=prizewinners)
        return render(
            request, 'admin/tracker/automail_prize_winners.html', {'form': form}
        )

    @staticmethod
    @permission_required('tracker.change_prizewinner')
    def preview_prize_winner_mail(request, prize_winner):
        # this should really be a helper
        import post_office.mail

        try:
            prize_winner = models.PrizeWinner.objects.get(pk=prize_winner)
        except models.PrizeWinner.DoesNotExist:
            raise Http404
        if not prize_winner.prize.event.prizewinneremailtemplate:
            return HttpResponse('event for prize has no prize winner template')
        prize_winner.create_claim_url(request)
        format_context = {
            'event': prize_winner.prize.event,
            'winner': prize_winner.winner,
            'prize_wins': [prize_winner],
            'multi': False,
            'prize_count': 1,
            'reply_address': 'preview@example.com',
            'accept_deadline': prize_winner.accept_deadline_date(),
        }
        return HttpResponse(
            post_office.mail.create(
                'preview@example.com',
                template=prize_winner.prize.event.prizewinneremailtemplate,
                context=format_context,
                commit=False,
            ).html_message,
            content_type='text/plain; charset=UTF-8',
        )

    @staticmethod
    @permission_required('tracker.change_prizewinner')
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
                    'admin/tracker/automail_prize_winners_accept_notifications_post.html',
                    {'prizewinners': form.cleaned_data['prizewinners']},
                )
        else:
            form = forms.AutomailPrizeAcceptNotifyForm(prizewinners=prizewinners)
        return render(
            request,
            'admin/tracker/automail_prize_winners_accept_notifications.html',
            {'form': form},
        )

    @staticmethod
    @permission_required('tracker.change_prizewinner')
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
                    'admin/tracker/automail_prize_winners_shipping_notifications_post.html',
                    {'prizewinners': form.cleaned_data['prizewinners']},
                )
        else:
            form = forms.AutomailPrizeShippingNotifyForm(prizewinners=prizewinners)
        return render(
            request,
            'admin/tracker/automail_prize_winners_shipping_notifications.html',
            {'form': form},
        )

    @staticmethod
    @permission_required('tracker.change_prize')
    def process_prize_submissions(request):
        currentEvent = viewutil.get_selected_event(request)
        return render(
            request,
            'admin/tracker/process_prize_submissions.html',
            {
                'currentEvent': currentEvent,
                'apiUrls': mark_safe(json.dumps(api_urls())),
            },
        )

    def get_urls(self):
        return super(PrizeAdmin, self).get_urls() + [
            url(
                'automail_prize_contributors',
                self.admin_site.admin_view(self.automail_prize_contributors),
                name='automail_prize_contributors',
            ),
            url(
                'draw_prize_winners',
                self.admin_site.admin_view(self.draw_prize_winners),
                name='draw_prize_winners',
            ),
            url(
                r'prize_key_import/(?P<prize>\d+)',
                self.admin_site.admin_view(self.prize_key_import),
                name='tracker_prize_key_import',
            ),
            url(
                'automail_prize_winners',
                self.admin_site.admin_view(self.automail_prize_winners),
                name='automail_prize_winners',
            ),
            url(
                r'preview_prize_winner_mail/(?P<prize_winner>\d+)',
                self.admin_site.admin_view(self.preview_prize_winner_mail),
                name='preview_prize_winner_mail',
            ),
            url(
                'automail_prize_accept_notifications',
                self.admin_site.admin_view(self.automail_prize_accept_notifications),
                name='automail_prize_accept_notifications',
            ),
            url(
                'automail_prize_shipping_notifications',
                self.admin_site.admin_view(self.automail_prize_shipping_notifications),
                name='automail_prize_shipping_notifications',
            ),
            url(
                'process_prize_submissions',
                self.admin_site.admin_view(self.process_prize_submissions),
                name='process_prize_submissions',
            ),
        ]


@register(models.PrizeKey)
class PrizeKeyAdmin(CustomModelAdmin):
    readonly_fields = (
        'prize',
        'prize_winner',
        'key',
    )  # don't allow editing of anything by default
