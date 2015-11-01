from django.contrib.auth.decorators import login_required

from . import common as views_common
import tracker.models as models
import tracker.forms as forms
import tracker.viewutil as viewutil
import tracker.filters as filters

import json

__all__ = [
    'submit_prize',
]

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
