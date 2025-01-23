import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpResponse

import tracker.forms as forms
import tracker.models as models
import tracker.search_filters as filters
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
    eventSet = {}

    for futureEvent in filters.run_model_query('event', {'feed': 'future'}):
        if not futureEvent.locked:
            eventDict = eventSet.setdefault(futureEvent, {'event': futureEvent})
            eventDict['submission'] = futureEvent

    for prize in models.Prize.objects.filter(handler=request.user):
        eventDict = eventSet.setdefault(prize.event, {'event': prize.event})
        prizeList = eventDict.setdefault('prizes', [])
        prizeList.append(prize)

    eventList = []

    for key, value in eventSet.items():
        value['eventname'] = value['event'].name
        value['eventid'] = value['event'].id
        value.setdefault('submission', False)
        eventList.append(value)

    eventList.sort(key=lambda x: x['event'].date)

    return views_common.tracker_response(
        request,
        'tracker/user_index.html',
        {
            'eventList': eventList,
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
        prize = models.Prize.objects.get(pk=prize)
    except ObjectDoesNotExist:
        raise Http404
    if (
        request.user != prize.handler
        and request.user != prize.event.prizecoordinator
        and not request.user.is_superuser
    ):
        return HttpResponse('You are not authorized to view this resource', 403)
    acceptedWinners = (
        prize.get_prize_winners().filter(Q(acceptcount__gte=1)).select_related('winner')
    )
    pendingWinners = (
        prize.get_prize_winners()
        .filter(Q(pendingcount__gte=1))
        .select_related('winner')
    )
    formset = None
    if request.method == 'POST':
        if acceptedWinners.exists():
            formset = forms.PrizeShippingFormSet(
                data=request.POST, queryset=acceptedWinners
            )
            savedForm = find_saved_form(request.POST, len(formset.forms), 'form-saved-')
            formset.extra = 0
            if savedForm is not None:
                targetForm = formset.forms[savedForm]
                if targetForm.is_valid():
                    targetForm.save()
                    targetForm.saved = True
    else:
        if acceptedWinners.exists():
            formset = forms.PrizeShippingFormSet(queryset=acceptedWinners)
            formset.extra = 0
    return views_common.tracker_response(
        request,
        'tracker/contributor_prize.html',
        dict(prize=prize, formset=formset, pendingWinners=pendingWinners),
    )


def prize_winner(request, prize_win):
    auth_code = request.GET.get('auth_code', None)
    try:
        prize_win = models.PrizeWinner.objects.get(
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

    # TODO: locked events should 404 here

    if request.method == 'POST':
        prizeForm = forms.PrizeSubmissionForm(data=request.POST)
        if prizeForm.is_valid():
            prize = prizeForm.save(event, request.user)
            return views_common.tracker_response(
                request, 'tracker/submit_prize_success.html', {'prize': prize}
            )
    else:
        prizeForm = forms.PrizeSubmissionForm()

    runs = filters.run_model_query(
        'run', {'event': event}, request.user
    ).prefetch_related('runners')

    def run_info(run):
        return {
            'id': run.id,
            'name': run.name,
            'description': run.description,
            'runners': run.runners_text,
            'starttime': run.starttime.isoformat(),
            'endtime': run.endtime.isoformat(),
        }

    dumpArray = [run_info(o) for o in runs.all()]
    runsJson = json.dumps(dumpArray)

    return views_common.tracker_response(
        request,
        'tracker/submit_prize.html',
        {'event': event, 'form': prizeForm, 'runs': runsJson},
    )
