import datetime
import logging
from decimal import Decimal

import pytz
from django.db import transaction
from django.http import Http404, HttpResponsePermanentRedirect
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from paypal.standard.forms import PayPalPaymentsForm
from tracker import forms, models, eventutil, viewutil, paypalutil
from . import common as views_common

__all__ = [
    'paypal_cancel',
    'paypal_return',
    'donate',
]

logger = logging.getLogger(__name__)


@csrf_exempt
def paypal_cancel(request):
    return views_common.tracker_response(request, 'tracker/paypal_cancel.html')


@csrf_exempt
def paypal_return(request):
    return views_common.tracker_response(request, 'tracker/paypal_return.html')


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
