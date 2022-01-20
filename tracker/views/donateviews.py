import datetime
import logging
import random
import traceback
from decimal import Decimal

import post_office.mail
import pytz
from django.db import transaction
from django.http import HttpResponse, Http404, HttpResponsePermanentRedirect
from django.urls import reverse
from django.views.decorators.cache import never_cache, cache_page
from django.views.decorators.csrf import csrf_exempt
from paypal.standard.forms import PayPalPaymentsForm
from tracker import forms, models, eventutil, viewutil, paypalutil
from tracker.analytics import analytics, AnalyticsEventTypes
from . import common as views_common

__all__ = [
    'paypal_cancel',
    'paypal_return',
    'donate',
    'ipn',
]

logger = logging.getLogger(__name__)


@csrf_exempt
def paypal_cancel(request):
    return views_common.tracker_response(request, 'tracker/paypal_cancel.html')


@csrf_exempt
def paypal_return(request):
    return views_common.tracker_response(request, 'tracker/paypal_return.html')


def _get_donation_event_fields(donation):
    has_comment = donation.comment is not None and donation.comment.strip() != ''
    return {
        'event_id': donation.event.id,
        'donation_id': donation.id,
        'amount': donation.amount,
        'is_anonymous': donation.anonymous(),
        'num_bids': donation.bids.count(),
        'currency': donation.currency,
        'has_comment': has_comment,
        'comment_language': donation.commentlanguage,
        'domain': donation.domain,
        # TODO: Update to track these fields properly
        'is_first_donation': False,
        'from_partner': False,
    }


# Fired when a donation is first received from our donation form
def _track_donation_received(donation):
    analytics.track(
        AnalyticsEventTypes.DONATION_RECEIVED,
        {**_get_donation_event_fields(donation), 'timestamp': donation.timereceived},
    )


# Fired when the payment processor tells us that the donation cannot yet
# be confirmed, for any reason.
def _track_donation_pending(donation, ipn, receivers_fault):
    analytics.track(
        AnalyticsEventTypes.DONATION_PENDING,
        {
            **_get_donation_event_fields(donation),
            'timestamp': pytz.utc.localize(datetime.datetime.utcnow()),
            'pending_reason': ipn.pending_reason,
            'reason_code': ipn.reason_code,
            'receivers_fault': receivers_fault,
        },
    )


# Fired when the donation has cleared the payment processor and confirmed deposit.
def _track_donation_completed(donation):
    analytics.track(
        AnalyticsEventTypes.DONATION_COMPLETED,
        {
            **_get_donation_event_fields(donation),
            'timestamp': pytz.utc.localize(datetime.datetime.utcnow()),
        },
    )


# Fired when the donation is cancelled or reversed through the payment processor.
def _track_donation_cancelled(donation):
    analytics.track(
        AnalyticsEventTypes.DONATION_CANCELLED,
        {
            **_get_donation_event_fields(donation),
            'timestamp': pytz.utc.localize(datetime.datetime.utcnow()),
        },
    )


def process_form(request, event):
    bidsFormPrefix = 'bidsform'
    if request.method == 'POST':
        commentform = forms.DonationEntryForm(event=event, data=request.POST)
        if commentform.is_valid():
            bidsform = forms.DonationBidFormSet(
                amount=commentform.cleaned_data['amount'],
                data=request.POST,
                prefix=bidsFormPrefix,
            )
            if bidsform.is_valid():
                with transaction.atomic():
                    donation = models.Donation(
                        amount=commentform.cleaned_data['amount'],
                        timereceived=pytz.utc.localize(datetime.datetime.utcnow()),
                        domain='PAYPAL',
                        domainId=str(random.getrandbits(128)),
                        event=event,
                    )
                    if commentform.cleaned_data['comment']:
                        donation.comment = commentform.cleaned_data['comment']
                        donation.commentstate = 'PENDING'
                    donation.requestedvisibility = commentform.cleaned_data[
                        'requestedvisibility'
                    ]
                    donation.requestedalias = commentform.cleaned_data['requestedalias']
                    donation.requestedemail = commentform.cleaned_data['requestedemail']
                    donation.requestedsolicitemail = commentform.cleaned_data[
                        'requestedsolicitemail'
                    ]
                    donation.currency = event.paypalcurrency
                    donation.save()
                    for bidform in bidsform:
                        if (
                            'bid' in bidform.cleaned_data
                            and bidform.cleaned_data['bid']
                        ):
                            bid = bidform.cleaned_data['bid']
                            if bid.allowuseroptions:
                                # unfortunately, you can't use get_or_create when using a non-atomic transaction
                                # this does technically introduce a race condition, I'm just going to hope that two people don't
                                # suggest the same option at the exact same time
                                # also, I want to do case-insensitive comparison on the name
                                try:
                                    bid = models.Bid.objects.get(
                                        event=bid.event,
                                        speedrun=bid.speedrun,
                                        name__iexact=bidform.cleaned_data[
                                            'customoptionname'
                                        ],
                                        parent=bid,
                                    )
                                except models.Bid.DoesNotExist:
                                    bid = models.Bid.objects.create(
                                        event=bid.event,
                                        speedrun=bid.speedrun,
                                        name=bidform.cleaned_data['customoptionname'],
                                        parent=bid,
                                        state='PENDING',
                                        istarget=True,
                                    )
                            donation.bids.add(
                                models.DonationBid(
                                    bid=bid,
                                    amount=Decimal(bidform.cleaned_data['amount']),
                                ),
                                bulk=False,
                            )
                    donation.full_clean()
                    donation.save()

                _track_donation_received(donation)

                paypal_dict = {
                    'amount': str(donation.amount),
                    'cmd': '_donations',
                    'business': donation.event.paypalemail,
                    'image_url': donation.event.paypalimgurl,
                    'item_name': donation.event.receivername,
                    'notify_url': request.build_absolute_uri(reverse('tracker:ipn')),
                    'return': request.build_absolute_uri(
                        reverse('tracker:paypal_return')
                    ),
                    'cancel_return': request.build_absolute_uri(
                        reverse('tracker:paypal_cancel')
                    ),
                    'custom': str(donation.id) + ':' + donation.domainId,
                    'currency_code': donation.event.paypalcurrency,
                    'no_shipping': 0,
                }
                # Create the form instance
                form = PayPalPaymentsForm(button_type='donate', initial=paypal_dict)
                context = {'event': donation.event, 'form': form}
                return (
                    views_common.tracker_response(
                        request, 'tracker/paypal_redirect.html', context
                    ),
                    None,
                )
        else:
            bidsform = forms.DonationBidFormSet(
                amount=Decimal('0.00'), data=request.POST, prefix=bidsFormPrefix
            )
            bidsform.is_valid()
    else:
        commentform = forms.DonationEntryForm(event=event)
        bidsform = forms.DonationBidFormSet(
            amount=Decimal('0.00'), prefix=bidsFormPrefix
        )
    return commentform, bidsform


@csrf_exempt
@cache_page(300)
def donate(request, event):
    event = viewutil.get_event(event)
    if event.locked or not event.allow_donations:
        raise Http404
    return HttpResponsePermanentRedirect(reverse('tracker:ui:donate', args=(event.id,)))


@csrf_exempt
@never_cache
def ipn(request):
    ipnObj = None

    if request.method == 'GET' or len(request.POST) == 0:
        return views_common.tracker_response(request, 'tracker/badobject.html', {})

    try:
        ipnObj = paypalutil.create_ipn(request)
        ipnObj.save()

        donation = paypalutil.initialize_paypal_donation(ipnObj)
        donation.save()

        if donation.transactionstate == 'PENDING':
            reasonExplanation, ourFault = paypalutil.get_pending_reason_details(
                ipnObj.pending_reason
            )
            if donation.event.pendingdonationemailtemplate:
                formatContext = {
                    'event': donation.event,
                    'donation': donation,
                    'donor': donation.donor,
                    'pending_reason': ipnObj.pending_reason,
                    'reason_info': reasonExplanation if not ourFault else '',
                }
                post_office.mail.send(
                    recipients=[donation.donor.email],
                    sender=donation.event.donationemailsender,
                    template=donation.event.pendingdonationemailtemplate,
                    context=formatContext,
                )
            # some pending reasons can be a problem with the receiver account, we should keep track of them
            if ourFault:
                paypalutil.log_ipn(ipnObj, 'Unhandled pending error')

            _track_donation_pending(donation, ipnObj, ourFault)
        elif donation.transactionstate == 'COMPLETED':
            if donation.event.donationemailtemplate is not None:
                formatContext = {
                    'donation': donation,
                    'donor': donation.donor,
                    'event': donation.event,
                    'prizes': viewutil.get_donation_prize_info(donation),
                }
                post_office.mail.send(
                    recipients=[donation.donor.email],
                    sender=donation.event.donationemailsender,
                    template=donation.event.donationemailtemplate,
                    context=formatContext,
                )
            eventutil.post_donation_to_postbacks(donation)
            _track_donation_completed(donation)

        elif donation.transactionstate == 'CANCELLED':
            # eventually we may want to send out e-mail for some of the possible cases
            # such as payment reversal due to double-transactions (this has happened before)
            paypalutil.log_ipn(ipnObj, 'Cancelled/reversed payment')
            _track_donation_cancelled(donation)

    except Exception as inst:
        # just to make sure we have a record of it somewhere
        logging.error('ERROR IN IPN RESPONSE, FIX IT')
        if ipnObj:
            paypalutil.log_ipn(
                ipnObj,
                '{0} \n {1}. POST data : {2}'.format(
                    inst, traceback.format_exc(), request.POST
                ),
            )
        else:
            viewutil.tracker_log(
                'paypal',
                'IPN creation failed: {0} \n {1}. POST data : {2}'.format(
                    inst, traceback.format_exc(), request.POST
                ),
            )
    return HttpResponse('OKAY')
