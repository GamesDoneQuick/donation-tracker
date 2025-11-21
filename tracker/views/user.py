from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import Http404

import tracker.forms as forms
import tracker.models as models
import tracker.viewutil as viewutil
from tracker.views import common as views_common

__all__ = [
    'user_index',
    'submit_prize',
    'user_prize',
    'prize_winner',
]


@login_required
def user_index(request):
    events = defaultdict(lambda: {'submission': False, 'prizes': []})

    for futureEvent in models.Event.objects.future():
        events[futureEvent]['submission'] = futureEvent

    for prize in models.Prize.objects.filter(handler=request.user).select_related(
        'event'
    ):
        events[prize.event]['prizes'].append(prize)

    return views_common.tracker_response(
        request,
        'tracker/user_index.html',
        {
            'event_list': sorted(events.items(), key=lambda e: e[0].date),
        },
    )


def find_saved_form(data, count, prefix):
    for i in range(0, count):
        if prefix + str(i + 1) in data:
            return i
    return None


@login_required
def user_prize(request, prize):
    try:
        prize = models.Prize.objects.prefetch_related('claims').get(pk=prize)
    except ObjectDoesNotExist:
        raise Http404
    if (
        request.user != prize.handler
        and request.user != prize.event.prizecoordinator
        and not request.user.is_superuser
    ):
        raise Http404
    accepted_claims = prize.get_accepted_claims()
    pending_claims = prize.get_pending_claims()
    if accepted_claims:
        formset = forms.PrizeShippingFormSet(
            prefix='prize_shipping',
            queryset=models.PrizeClaim.objects.filter(
                id__in=(c.id for c in accepted_claims)
            ).select_related('winner'),
            data=request.POST if request.method == 'POST' else None,
        )
        formset.extra = 0

        if formset.is_valid():
            formset.save()
    else:
        formset = None
    return views_common.tracker_response(
        request,
        'tracker/contributor_prize.html',
        {'prize': prize, 'formset': formset, 'pending_claims': pending_claims},
    )


def prize_winner(request, prize_win):
    auth_code = request.GET.get('auth_code', None)
    try:
        prize_win = models.PrizeClaim.objects.get(
            pk=prize_win, auth_code__iexact=auth_code
        )
    except ObjectDoesNotExist:
        raise Http404
    if request.method == 'POST':
        if prize_win.prize.requiresshipping:
            address_form = forms.AddressForm(
                prefix='address', instance=prize_win.winner, data=request.POST
            )
        else:
            address_form = None
        acceptance_form = forms.PrizeAcceptanceForm(
            prefix='prizeaccept', instance=prize_win, data=request.POST
        )
        if acceptance_form.is_valid() and (not address_form or address_form.is_valid()):
            with transaction.atomic():
                acceptance_form.save()
                if address_form:
                    address_form.save()
    else:
        if prize_win.prize.requiresshipping:
            address_form = forms.AddressForm(
                prefix='address', instance=prize_win.winner
            )
        else:
            address_form = None
        acceptance_form = forms.PrizeAcceptanceForm(
            prefix='prizeaccept', instance=prize_win
        )

    return views_common.tracker_response(
        request,
        'tracker/prize_winner.html',
        dict(
            acceptance_form=acceptance_form,
            address_form=address_form,
            prize=prize_win.prize,
            prize_win=prize_win,
        ),
    )


@login_required
def submit_prize(request, event):
    event = viewutil.get_event(event)

    if event.archived:
        raise Http404

    initial = {'event': event.id}
    if request.user.username != getattr(
        request.user, request.user.get_email_field_name(), ''
    ):
        initial['provider'] = request.user.username

    form = forms.PrizeSubmissionForm(
        initial=initial,
        data=request.POST if request.method == 'POST' else None,
    )

    if form.is_valid():
        prize = form.save(event, request.user)
        return views_common.tracker_response(
            request, 'tracker/submit_prize_success.html', {'prize': prize, 'form': form}
        )

    return views_common.tracker_response(
        request,
        'tracker/submit_prize.html',
        {'event': event, 'form': form},
    )
