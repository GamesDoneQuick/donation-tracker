from . import common as views_common
import donation_tracker.models as models
import donation_tracker.forms as forms
import donation_tracker.viewutil as viewutil
import donation_tracker.filters as filters

from django.views.decorators.csrf import csrf_exempt

import json

__all__ = [
  'submit_prize',
  ]

@csrf_exempt
def submit_prize(request, event):
  event = viewutil.get_event(event)
  if request.method == 'POST':
    prizeForm = forms.PrizeSubmissionForm(data=request.POST)
    if prizeForm.is_valid():
      prize = models.Prize.objects.create(
        event=event,
        name=prizeForm.cleaned_data['name'],
        description=prizeForm.cleaned_data['description'],
        maxwinners=prizeForm.cleaned_data['maxwinners'],
        extrainfo=prizeForm.cleaned_data['extrainfo'],
        estimatedvalue=prizeForm.cleaned_data['estimatedvalue'],
        minimumbid=prizeForm.cleaned_data['suggestedamount'],
        maximumbid=prizeForm.cleaned_data['suggestedamount'],
        image=prizeForm.cleaned_data['imageurl'],
        provided=prizeForm.cleaned_data['providername'],
        provideremail=prizeForm.cleaned_data['provideremail'],
        creator=prizeForm.cleaned_data['creatorname'],
        creatoremail=prizeForm.cleaned_data['creatoremail'],
        creatorwebsite=prizeForm.cleaned_data['creatorwebsite'],
        startrun=prizeForm.cleaned_data['startrun'],
        endrun=prizeForm.cleaned_data['endrun'])
      prize.save()
      return views_common.tracker_response(request, "donation_tracker/submit_prize_success.html", { 'prize': prize })
  else:
    prizeForm = forms.PrizeSubmissionForm()

  runs = filters.run_model_query('run', {'event': event}, request.user)

  def run_info(run):
    return {'id': run.id, 'name': run.name, 'description': run.description, 'runners': run.deprecated_runners, 'starttime': run.starttime.isoformat(), 'endtime': run.endtime.isoformat() }

  dumpArray = [run_info(o) for o in runs.all()]
  runsJson = json.dumps(dumpArray)

  return views_common.tracker_response(request, "donation_tracker/submit_prize_form.html", { 'event': event, 'form': prizeForm, 'runs': runsJson })
