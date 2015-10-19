import django
import traceback

from django import shortcuts
from django.shortcuts import render,render_to_response, redirect

from django.db import connection
from django.db.models import Count,Sum,Max,Avg,Q
from django.db.utils import ConnectionDoesNotExist,IntegrityError
from django.db import transaction

from django.forms import ValidationError

from django.core import serializers,paginator
from django.core.paginator import Paginator
from django.core.cache import cache
from django.core.exceptions import FieldError,ObjectDoesNotExist
from django.core.urlresolvers import reverse

from django.contrib.auth import authenticate,login as auth_login,logout as auth_logout, get_user_model
from django.contrib.auth.forms import AuthenticationForm
import django.contrib.auth.views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator

from django.http import HttpResponse,HttpResponseRedirect,Http404

from django import template
from django.template import RequestContext
from django.template.base import TemplateSyntaxError

from django.views.decorators.cache import never_cache,cache_page
from django.views.decorators.csrf import csrf_protect,csrf_exempt,get_token as get_csrf_token
from django.views.decorators.http import require_POST

import post_office.mail

from django.utils import translation
from django.utils.http import urlsafe_base64_decode
import json

from paypal.standard.forms import PayPalPaymentsForm
from paypal.standard.ipn.models import PayPalIPN
from paypal.standard.ipn.forms import PayPalIPNForm

from tracker.models import *
from tracker.forms import *
import tracker.filters as filters

import tracker.viewutil as viewutil
import tracker.paypalutil as paypalutil
from tracker.views.common import fixorder, tracker_response

import gdata.spreadsheet.service
import gdata.spreadsheet.text_db

from decimal import Decimal
import sys
import datetime
import settings
import tracker.logutil as log
import pytz
import random
import decimal
import re
import dateutil.parser
import itertools
import urllib2

from tracker.views.auth import __all__ as all_auth_views
from tracker.views.auth import *

from tracker.views.public import __all__ as all_public_views
from tracker.views.public import *

from tracker.views.api import __all__ as all_api_views
from tracker.views.api import *

from tracker.views.donateviews import __all__ as all_donate_views
from tracker.views.donateviews import *

__all__ = all_auth_views + all_public_views + all_api_views + all_donate_views + [
  'submit_prize',
  ]

@csrf_exempt
def submit_prize(request, event):
  event = viewutil.get_event(event)
  if request.method == 'POST':
    prizeForm = PrizeSubmissionForm(data=request.POST)
    if prizeForm.is_valid():
      prize = Prize.objects.create(
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
      return tracker_response(request, "tracker/submit_prize_success.html", { 'prize': prize })
  else:
    prizeForm = PrizeSubmissionForm()

  runs = filters.run_model_query('run', {'event': event}, request.user)

  def run_info(run):
    return {'id': run.id, 'name': run.name, 'description': run.description, 'runners': run.deprecated_runners, 'starttime': run.starttime.isoformat(), 'endtime': run.endtime.isoformat() }

  dumpArray = [run_info(o) for o in runs.all()]
  runsJson = json.dumps(dumpArray)

  return tracker_response(request, "tracker/submit_prize_form.html", { 'event': event, 'form': prizeForm, 'runs': runsJson })
