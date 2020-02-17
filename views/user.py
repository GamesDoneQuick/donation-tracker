import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import HttpResponse, Http404

import tracker.forms as forms
import tracker.models as models
import tracker.search_filters as filters
from tracker.views import common as views_common
import tracker.viewutil as viewutil

__all__ = [
    'user_index',
    'submit_prize',
    'user_prize',
    'prize_winner',
]


@login_required
def user_index(request):
    event_set = {}

    for future_event in filters.run_model_query('event', {'feed': 'future'}):
        if not future_event.locked:
            event_dict = event_set.setdefault(future_event, {'event': future_event})
            event_dict['submission'] = future_event

    for prize in models.Prize.objects.filter(handler=request.user):
        event_dict = event_set.setdefault(prize.event, {'event': prize.event})
        prize_list = event_dict.setdefault('prizes', [])
        prize_list.append(prize)

    event_list = []

    for key, value in event_set.items():
        value['eventname'] = value['event'].name
        value['eventid'] = value['event'].id
        value.setdefault('submission', False)
        event_list.append(value)

    event_list.sort(key=lambda x: x['event'].date)

    return views_common.tracker_response(
        request, 'tracker/user_index.html', {'event_list': event_list,}
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
    accepted_winners = (
        prize.get_prize_winners().filter(Q(acceptcount__gte=1)).select_related('winner')
    )
    pending_winners = (
        prize.get_prize_winners()
        .filter(Q(pendingcount__gte=1))
        .select_related('winner')
    )
    formset = None
    if request.method == 'POST':
        if accepted_winners.exists():
            formset = forms.PrizeShippingFormSet(
                data=request.POST, queryset=accepted_winners
            )
            saved_form = find_saved_form(
                request.POST, len(formset.forms), 'form-saved-'
            )
            formset.extra = 0
            if saved_form is not None:
                target_form = formset.forms[saved_form]
                if target_form.is_valid():
                    target_form.save()
                    target_form.saved = True
    else:
        if accepted_winners.exists():
            formset = forms.PrizeShippingFormSet(queryset=accepted_winners)
            formset.extra = 0
    return views_common.tracker_response(
        request,
        'tracker/contributor_prize.html',
        dict(prize=prize, formset=formset, pending_winners=pending_winners),
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
        form = forms.PrizeAcceptanceWithAddressForm(
            instance={'address': prize_win.winner, 'prizeaccept': prize_win,},
            data=request.POST,
        )
        if form.is_valid():
            form.save()
        else:
            # this is a special case where we need to reset the model instance
            # for the page to work
            prize_win = models.PrizeWinner.objects.get(id=prize_win.id)
    else:
        form = forms.PrizeAcceptanceWithAddressForm(
            instance={'address': prize_win.winner, 'prizeaccept': prize_win,}
        )

    return views_common.tracker_response(
        request,
        'tracker/prize_winner.html',
        dict(form=form, prize=prize_win.prize, prize_win=prize_win),
    )


@login_required
def submit_prize(request, event):
    event = viewutil.get_event(event)

    # TODO: locked events should 404 here

    if request.method == 'POST':
        prize_form = forms.PrizeSubmissionForm(data=request.POST)
        if prize_form.is_valid():
            prize = prize_form.save(event, request.user)
            return views_common.tracker_response(
                request, 'tracker/submit_prize_success.html', {'prize': prize}
            )
    else:
        prize_form = forms.PrizeSubmissionForm()

    runs = filters.run_model_query('run', {'event': event}, request.user)

    def run_info(run):
        return {
            'id': run.id,
            'name': run.name,
            'description': run.description,
            'runners': run.deprecated_runners,
            'starttime': run.starttime.isoformat(),
            'endtime': run.endtime.isoformat(),
        }

    dump_array = [run_info(o) for o in runs.all()]
    runs_json = json.dumps(dump_array)

    return views_common.tracker_response(
        request,
        'tracker/submit_prize.html',
        {'event': event, 'form': prize_form, 'runs': runs_json},
    )
