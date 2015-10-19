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

__all__ = all_auth_views + all_public_views + all_api_views + [
  'submit_prize',
  'paypal_cancel',
  'paypal_return',
  'donate',
  'ipn',
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

@csrf_exempt
def paypal_cancel(request):
  return tracker_response(request, "tracker/paypal_cancel.html")

@csrf_exempt
def paypal_return(request):
  return tracker_response(request, "tracker/paypal_return.html")

@transaction.atomic
@csrf_exempt
def donate(request, event):
  event = viewutil.get_event(event)
  if event.locked:
    raise Http404
  bidsFormPrefix = "bidsform"
  prizeFormPrefix = "prizeForm"
  if request.method == 'POST':
    commentform = DonationEntryForm(data=request.POST)
    if commentform.is_valid():
      prizesform = PrizeTicketFormSet(amount=commentform.cleaned_data['amount'], data=request.POST, prefix=prizeFormPrefix)
      bidsform = DonationBidFormSet(amount=commentform.cleaned_data['amount'], data=request.POST, prefix=bidsFormPrefix)
      if bidsform.is_valid() and prizesform.is_valid():
        try:
          donation = Donation(amount=commentform.cleaned_data['amount'], timereceived=pytz.utc.localize(datetime.datetime.utcnow()), domain='PAYPAL', domainId=str(random.getrandbits(128)), event=event, testdonation=event.usepaypalsandbox)
          if commentform.cleaned_data['comment']:
            donation.comment = commentform.cleaned_data['comment']
            donation.commentstate = "PENDING"
          donation.requestedvisibility = commentform.cleaned_data['requestedvisibility']
          donation.requestedalias = commentform.cleaned_data['requestedalias']
          donation.requestedemail = commentform.cleaned_data['requestedemail']
          donation.currency = event.paypalcurrency
          donation.save()
          for bidform in bidsform:
            if 'bid' in bidform.cleaned_data and bidform.cleaned_data['bid']:
              bid = bidform.cleaned_data['bid']
              if bid.allowuseroptions:
                # unfortunately, you can't use get_or_create when using a non-atomic transaction
                # this does technically introduce a race condition, I'm just going to hope that two people don't
                # suggest the same option at the exact same time
                # also, I want to do case-insensitive comparison on the name
                try:
                  bid = Bid.objects.get(event=bid.event, speedrun=bid.speedrun, name__iexact=bidform.cleaned_data['customoptionname'], parent=bid)
                except Bid.DoesNotExist:
                  bid = Bid.objects.create(event=bid.event, speedrun=bid.speedrun, name=bidform.cleaned_data['customoptionname'], parent=bid, state='PENDING', istarget=True)
              donation.bids.add(DonationBid(bid=bid, amount=Decimal(bidform.cleaned_data['amount'])))
          for prizeform in prizesform:
            if 'prize' in prizeform.cleaned_data and prizeform.cleaned_data['prize']:
              prize = prizeform.cleaned_data['prize']
              donation.tickets.add(PrizeTicket(prize=prize, amount=Decimal(prizeform.cleaned_data['amount'])))
          donation.full_clean()
          donation.save()
        except Exception as e:
          transaction.rollback()
          raise e

        serverURL = viewutil.get_request_server_url(request)

        paypal_dict = {
          "amount": str(donation.amount),
          "cmd": "_donations",
          "business": donation.event.paypalemail,
          "item_name": donation.event.receivername,
          "notify_url": serverURL + reverse('tracker.views.ipn'),
          "return_url": serverURL + reverse('tracker.views.paypal_return'),
          "cancel_return": serverURL + reverse('tracker.views.paypal_cancel'),
          "custom": str(donation.id) + ":" + donation.domainId,
          "currency_code": donation.event.paypalcurrency,
        }
        # Create the form instance
        form = PayPalPaymentsForm(button_type="donate", sandbox=donation.event.usepaypalsandbox, initial=paypal_dict)
        context = {"event": donation.event, "form": form }
        return tracker_response(request, "tracker/paypal_redirect.html", context)
    else:
      bidsform = DonationBidFormSet(amount=Decimal('0.00'), data=request.POST, prefix=bidsFormPrefix)
      prizesform = PrizeTicketFormSet(amount=Decimal('0.00'), data=request.POST, prefix=prizeFormPrefix)
  else:
    commentform = DonationEntryForm()
    bidsform = DonationBidFormSet(amount=Decimal('0.00'), prefix=bidsFormPrefix)
    prizesform = PrizeTicketFormSet(amount=Decimal('0.00'), prefix=prizeFormPrefix)

  def bid_parent_info(bid):
    if bid != None:
      return {'name': bid.name, 'description': bid.description, 'parent': bid_parent_info(bid.parent) }
    else:
      return None

  def bid_info(bid):
    result = {
      'id': bid.id,
      'name': bid.name,
      'description': bid.description,
      'label': bid.full_label(not bid.allowuseroptions),
      'count': bid.count,
      'amount': bid.total,
      'goal': Decimal(bid.goal or '0.00'),
      'parent': bid_parent_info(bid.parent)
    }
    if bid.speedrun:
      result['runname'] = bid.speedrun.name
    if bid.suggestions.exists():
      result['suggested'] = list(map(lambda x: x.name, bid.suggestions.all()))
    if bid.allowuseroptions:
      result['custom'] = ['custom']
      result['label'] += ' (select and add a name next to "New Option Name")'
    return result

  bids = filters.run_model_query('bidtarget', {'state':'OPENED', 'event':event.id }, user=request.user).distinct().select_related('parent').prefetch_related('suggestions')

  allPrizes = filters.run_model_query('prize', {'feed': 'current', 'event': event.id })

  prizes = allPrizes.filter(ticketdraw=False)

  dumpArray = [bid_info(o) for o in bids]
  bidsJson = json.dumps(dumpArray)

  ticketPrizes = allPrizes.filter(ticketdraw=True)

  def prize_info(prize):
    result = {'id': prize.id, 'name': prize.name, 'description': prize.description, 'minimumbid': prize.minimumbid, 'maximumbid': prize.maximumbid}
    return result

  dumpArray = [prize_info(o) for o in ticketPrizes.all()]
  ticketPrizesJson = json.dumps(dumpArray)

  return tracker_response(request, "tracker/donate.html", { 'event': event, 'bidsform': bidsform, 'prizesform': prizesform, 'commentform': commentform, 'hasBids': bids.count() > 0, 'bidsJson': bidsJson, 'hasTicketPrizes': ticketPrizes.count() > 0, 'ticketPrizesJson': ticketPrizesJson, 'prizes': prizes})

@csrf_exempt
@never_cache
def ipn(request):
  donation = None
  ipnObj = None

  if request.method == 'GET' or len(request.POST) == 0:
    return tracker_response(request, "tracker/badobject.html", {})

  try:
    ipnObj = paypalutil.create_ipn(request)
    ipnObj.save()

    donation = paypalutil.initialize_paypal_donation(ipnObj)
    donation.save()

    if donation.transactionstate == 'PENDING':
      reasonExplanation, ourFault = paypalutil.get_pending_reason_details(ipnObj.pending_reason)
      if donation.event.pendingdonationemailtemplate:
        formatContext = {
          'event': donation.event,
          'donation': donation,
          'donor': donor,
          'pending_reason': ipnObj.pending_reason,
          'reason_info': reasonExplanation if not ourFault else '',
        }
        post_office.mail.send(recipients=[donation.donor.email], sender=donation.event.donationemailsender, template=donation.event.pendingdonationemailtemplate, context=formatContext)
      # some pending reasons can be a problem with the receiver account, we should keep track of them
      if ourFault:
        paypalutil.log_ipn(ipnObj, 'Unhandled pending error')
    elif donation.transactionstate == 'COMPLETED':
      if donation.event.donationemailtemplate != None:
        formatContext = {
          'donation': donation,
          'donor': donation.donor,
          'event': donation.event,
          'prizes': viewutil.get_donation_prize_info(donation),
        }
        post_office.mail.send(recipients=[donation.donor.email], sender=donation.event.donationemailsender, template=donation.event.donationemailtemplate, context=formatContext)

      # TODO: this should eventually share code with the 'search' method, to
      postbackData = {
        'id': donation.id,
        'timereceived': str(donation.timereceived),
        'comment': donation.comment,
        'amount': donation.amount,
        'donor__visibility': donation.donor.visibility,
        'donor__visiblename': donation.donor.visible_name(),
      }
      postbackJSon = json.dumps(postbackData)
      postbacks = PostbackURL.objects.filter(event=donation.event)
      for postback in postbacks:
        opener = urllib2.build_opener()
        req = urllib2.Request(postback.url, postbackJSon, headers={'Content-Type': 'application/json; charset=utf-8'})
        response = opener.open(req, timeout=5)
    elif donation.transactionstate == 'CANCELLED':
      # eventually we may want to send out e-mail for some of the possible cases
      # such as payment reversal due to double-transactions (this has happened before)
      paypalutil.log_ipn(ipnObj, 'Cancelled/reversed payment')

  except Exception as inst:
    print(inst)
    print(traceback.format_exc(inst))
    if ipnObj:
      paypalutil.log_ipn(ipnObj, "{0} \n {1}. POST data : {2}".format(inst, traceback.format_exc(inst), request.POST))
    else:
      viewutil.tracker_log('paypal', 'IPN creation failed: {0} \n {1}. POST data : {2}'.format(inst, traceback.format_exc(inst), request.POST))

  return HttpResponse("OKAY")
