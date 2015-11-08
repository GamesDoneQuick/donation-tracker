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
]

@login_required
def user_index(request):
    eventSet = {}
    
    for futureEvent in filters.run_model_query('event', {'feed': 'future'}):
        eventDict = eventSet.setdefault(futureEvent, {'event': futureEvent})
        eventDict['submission'] = futureEvent

    for prize in models.Prize.objects.filter(provider=request.user):
        eventDict = eventSet.setdefault(prize.event, {'event': futureEvent})
        prizeList = eventDict.setdefault('prizes', [])
        prizeList.append(prize)

    donor = request.user.donor
    if donor != None:
        for prizeWin in models.PrizeWinner.objects.filter(Q(winner=donor)&(Q(pendingcount__gte=1)|Q(acceptcount__gte=1))):
            print(prizeWin)
            eventDict = eventSet.setdefault(prizeWin.prize.event, {'event': prizeWin.prize.event})
            prizeWinList = eventDict.setdefault('prizewins', [])
            prizeWinList.append(prizeWin)
        
    eventList = []
    
    for key,value in eventSet.iteritems():
        value['eventname'] = value['event'].name
        value['eventid'] = value['event'].id
        value.setdefault('submission', False)
        eventList.append(value)

    eventList.sort(key=lambda x: x['eventid'])

    return views_common.tracker_response(request, "tracker/user_index.html", {'eventList': eventList, })
        
def _contributor_prize_view(request, prize):
    pendingWinners = prize.get_prize_winners().filter(Q(pendingcount__gte=1)&Q(acceptcount=0))
    confirmedWinners = prize.get_prize_winners().filter(Q(acceptcount__gte=1))
    return views_common.tracker_response(request, "tracker/contributor_prize.html", dict(prize=prize, confirmedWinners=confirmedWinners, pendingWinners=pendingWinners))
        
def _winner_prize_view(request, prizeWin):
    if request.method == 'POST':
        form = forms.PrizeAcceptanceWithAddressForm(requiresShipping=prizeWin.prize.requiresshipping, instance={ 'address': prizeWin.winner, 'prizeaccept': prizeWin, }, data=request.POST, )
        if form.is_valid():
            form.save()
            prizeAcceptForm = form.forms['prizeaccept']
            acceptCount = prizeAcceptForm.cleaned_data['count']
            totalCount = prizeAcceptForm.cleaned_data['total']
            params = dict(acceptcount=acceptCount,declinecount=totalCount-acceptCount,prize=prizeWin.prize, prizeWin=prizeWin)
            return views_common.tracker_response(request, "tracker/winner_prize_complete.html", params)
    else:
        form = forms.PrizeAcceptanceWithAddressForm(requiresShipping=prizeWin.prize.requiresshipping, instance={ 'address': prizeWin.winner, 'prizeaccept': prizeWin, } )

    return views_common.tracker_response(request, "tracker/winner_prize.html", dict(form=form, prize=prizeWin.prize, prizeWin=prizeWin))
        
@login_required
def user_prize(request, prize):
    prize = models.Prize.objects.get(pk=prize)
    if request.user == prize.provider:
        return _contributor_prize_view(request, prize)
    else:
        donor = request.user.donor
        if donor != None:
            winnerQuerySet = prize.get_prize_winners().filter(winner=donor)
            if winnerQuerySet.exists():
                return _winner_prize_view(request, winnerQuerySet[0])
    return HttpResponse('You are not authorized to view this page', status=403)


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
