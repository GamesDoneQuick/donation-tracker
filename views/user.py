from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse

from . import common as views_common
import tracker.models as models
import tracker.forms as forms
import tracker.viewutil as viewutil
import tracker.filters as filters

import json

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
        eventDict = eventSet.setdefault(futureEvent, {'event': futureEvent})
        eventDict['submission'] = futureEvent

    for prize in models.Prize.objects.filter(handler=request.user):
        eventDict = eventSet.setdefault(prize.event, {'event': prize.event})
        prizeList = eventDict.setdefault('prizes', [])
        prizeList.append(prize)

    eventList = []

    for key, value in eventSet.iteritems():
        value['eventname'] = value['event'].name
        value['eventid'] = value['event'].id
        value.setdefault('submission', False)
        eventList.append(value)

    eventList.sort(key=lambda x: x['event'].date)

    return views_common.tracker_response(request, "tracker/user_index.html", {'eventList': eventList, })


def find_saved_form(data, count, prefix):
    for i in range(0, count):
        if prefix + str(i + 1) in data:
            return i
    return None


@login_required
def user_prize(request, prize):
    prize = models.Prize.objects.get(pk=prize)
    acceptedWinners = prize.get_prize_winners().filter(
        Q(acceptcount__gte=1)).select_related('winner')
    pendingWinners = prize.get_prize_winners().filter(
        Q(pendingcount__gte=1)).select_related('winner')
    formset = None
    if request.method == 'POST':
        if acceptedWinners.exists():
            formset = forms.PrizeShippingFormSet(
                data=request.POST, queryset=acceptedWinners)
            savedForm = find_saved_form(
                request.POST, len(formset.forms), 'form-saved-')
            formset.extra = 0
            if savedForm != None:
                targetForm = formset.forms[savedForm]
                if targetForm.is_valid():
                    targetForm.save()
                    targetForm.saved = True
    else:
        if acceptedWinners.exists():
            formset = forms.PrizeShippingFormSet(queryset=acceptedWinners)
            formset.extra = 0
    return views_common.tracker_response(request, "tracker/contributor_prize.html", dict(prize=prize, formset=formset, pendingWinners=pendingWinners))


def prize_winner(request, prize_win):
    authCode = request.GET.get('auth_code', None)
    prizeWin = models.PrizeWinner.objects.get(pk=prize_win, auth_code__iexact=authCode)
    if request.method == 'POST':
        form = forms.PrizeAcceptanceWithAddressForm(
            instance={'address': prizeWin.winner, 'prizeaccept': prizeWin, }, data=request.POST, )
        if form.is_valid():
            form.save()
            prizeAcceptForm = form.forms['prizeaccept']
            acceptCount = prizeAcceptForm.cleaned_data['count']
            totalCount = prizeAcceptForm.cleaned_data['total']
            params = dict(acceptcount=acceptCount, declinecount=totalCount -
                          acceptCount, prize=prizeWin.prize, prizeWin=prizeWin)
        else:
            # this is a special case where we need to reset the model instance
            # for the page to work
            prizeWin = models.PrizeWinner.objects.get(id=prizeWin.id)
    else:
        form = forms.PrizeAcceptanceWithAddressForm(
            instance={'address': prizeWin.winner, 'prizeaccept': prizeWin, })

    return views_common.tracker_response(request, "tracker/prize_winner.html", dict(form=form, prize=prizeWin.prize, prizeWin=prizeWin))


@login_required
def submit_prize(request, event):
    event = viewutil.get_event(event)

    if request.method == 'POST':
        prizeForm = forms.PrizeSubmissionForm(data=request.POST)
        if prizeForm.is_valid():
            prize = prizeForm.save(event, request.user)
            return views_common.tracker_response(request, "tracker/submit_prize_success.html", {'prize': prize})
    else:
        prizeForm = forms.PrizeSubmissionForm()

    runs = filters.run_model_query('run', {'event': event}, request.user)

    def run_info(run):
        return {'id': run.id, 'name': run.name, 'description': run.description, 'runners': run.deprecated_runners, 'starttime': run.starttime.isoformat(), 'endtime': run.endtime.isoformat()}

    dumpArray = [run_info(o) for o in runs.all()]
    runsJson = json.dumps(dumpArray)

    return views_common.tracker_response(request, "tracker/submit_prize.html", {'event': event, 'form': prizeForm, 'runs': runsJson})
