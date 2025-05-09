import datetime
import logging
from decimal import Decimal

from django.dispatch import receiver
from paypal.standard.ipn.signals import invalid_ipn_received, valid_ipn_received

import tracker.viewutil as viewutil
from tracker import settings, tasks, util
from tracker.analytics import AnalyticsEventTypes, analytics
from tracker.models import Country, Donation, Donor

logger = logging.getLogger(__name__)


class SpoofedIPNException(Exception):
    pass


def verify_ipn_recipient_email(ipn, email):
    """
    Raises SpoofedIPNException if the recipient in the IPN doesn't match
    the provided email.

    In IPNs, business is set the same as receiver_email if the payment
    was sent to the primary email of an account. If not, business is
    set to the account email in the transaction and receiver_email
    remains the primary email of an account.

    That is, for a payment to an account, business may change from
    transaction to transaction, but receiver_email stays the same as
    long as the recipient doesn't change their primary email.

    https://developer.paypal.com/docs/classic/ipn/integration-guide/IPNandPDTVariables/#mass-pay-variables
    """
    recipient_email = ipn.business if ipn.business else ipn.receiver_email
    if recipient_email.lower() != email.lower():
        raise SpoofedIPNException(
            f"IPN receiver `{recipient_email}` doesn't match `{email}`"
        )


def get_ipn_donation(ipnObj):
    if ipnObj.custom and ':' in ipnObj.custom:
        toks = ipnObj.custom.split(':')
        try:
            pk = int(toks[0])
        except ValueError:
            return None
        donation = Donation.objects.filter(pk=pk).prefetch_related('ipns').first()
        if donation:
            try:
                verify_ipn_recipient_email(ipnObj, donation.event.paypalemail)
            except SpoofedIPNException as e:
                viewutil.tracker_log('paypal', e)
                return None
            # if the donation amount does not match, or the custom field does not match an earlier IPN for the same
            # donation, ignore it, it means the form payload is corrupted somehow and cannot be trusted
            first = donation.ipns.first()
            if first is None:
                viewutil.tracker_log(
                    'paypal',
                    f'Could not find IPN for donation for IPN, this is a bug {ipnObj.id}',
                )
                logger.error(
                    f'Could not find IPN for donation for IPN, this is a bug {ipnObj.id}'
                )
                return None
            elif donation.amount == ipnObj.mc_gross and first.custom == ipnObj.custom:
                return donation
            viewutil.tracker_log(
                'paypal', f'IPN ignored, amount or signature did not match {ipnObj.id}'
            )
    return None


def fill_donor_address(donor, ipnObj):
    if not donor.addressstreet:
        donor.addressstreet = ipnObj.address_street
    if not donor.addresscity:
        donor.addresscity = ipnObj.address_city
    if not donor.addresscountry:
        countrycode = (
            ipnObj.residence_country
            if not ipnObj.address_country_code
            else ipnObj.address_country_code
        )
        donor.addresscountry = Country.objects.filter(alpha2=countrycode).first()
    if not donor.addressstate:
        donor.addressstate = ipnObj.address_state
    if not donor.addresszip:
        donor.addresszip = ipnObj.address_zip
    donor.save()


@receiver(valid_ipn_received)
def initialize_paypal_donation(*, sender, **kwargs):
    ipn = sender
    donation = get_ipn_donation(ipn)

    if donation is None:
        return

    defaults = {
        'email': ipn.payer_email.lower(),
        'firstname': ipn.first_name,
        'lastname': ipn.last_name,
        'visibility': 'ANON',
    }
    donor, created = Donor.objects.get_or_create(
        paypalemail=ipn.payer_email.lower(), defaults=defaults
    )

    fill_donor_address(donor, ipn)

    if donation.requestedvisibility != 'CURR':
        donor.visibility = donation.requestedvisibility
    if donation.requestedalias and (
        not donor.alias or donation.requestedalias.lower() != donor.alias.lower()
    ):
        donor.alias = donation.requestedalias
        donor.alias_num = None  # will get filled in by the donor save
    if (
        donation.requestedemail
        and donation.requestedemail != donor.email
        and not Donor.objects.filter(email=donation.requestedemail).exists()
    ):
        donor.email = donation.requestedemail
    if donation.requestedsolicitemail != 'CURR':
        donor.solicitemail = donation.requestedsolicitemail
    donor.save()

    donation.domain = 'PAYPAL'
    donation.domainId = ipn.txn_id
    donation.donor = donor
    donation.currency = ipn.mc_currency
    if not donation.timereceived:
        donation.timereceived = util.utcnow()
    donation.testdonation = ipn.test_ipn
    donation.fee = Decimal(ipn.mc_fee or 0)

    paymentStatus = ipn.payment_status.lower()

    if paymentStatus == 'pending':
        donation.transactionstate = 'PENDING'
    elif (
        paymentStatus == 'completed'
        or paymentStatus == 'canceled_reversal'
        or paymentStatus == 'processed'
    ):
        if donation.cleared_at is None:
            donation.cleared_at = ipn.created_at
        donation.transactionstate = 'COMPLETED'
    elif (
        paymentStatus == 'refunded'
        or paymentStatus == 'reversed'
        or paymentStatus == 'failed'
        or paymentStatus == 'voided'
        or paymentStatus == 'denied'
    ):
        donation.cleared_at = None
        donation.transactionstate = 'CANCELLED'
    else:
        donation.transactionstate = 'FLAGGED'
        viewutil.tracker_log(
            'paypal',
            'Unknown payment status in donation {0} ({1})'.format(
                donation.id, paymentStatus
            ),
            event=donation.event,
        )

    donation.save()

    if donation.transactionstate == 'COMPLETED':
        if settings.TRACKER_HAS_CELERY:
            tasks.post_donation_to_postbacks.delay(donation.id)
        else:
            tasks.post_donation_to_postbacks(donation.id)
        _track_donation_completed(donation)
    elif donation.transactionstate == 'PENDING':
        reasonExplanation, ourFault = get_pending_reason_details(ipn.pending_reason)
        _track_donation_pending(donation, ipn, ourFault)
    elif donation.transactionstate == 'CANCELLED':
        # eventually we may want to send out e-mail for some of the possible cases
        # such as payment reversal due to double-transactions (this has happened before)
        log_ipn(ipn, 'Cancelled/reversed payment')
        _track_donation_cancelled(donation)


@receiver(invalid_ipn_received)
def handle_ipn_error(*, sender, **kwargs):
    ipn = sender
    donation = get_ipn_donation(ipn)

    if donation is None:
        return

    donation.transactionstate = 'FLAGGED'
    viewutil.tracker_log(
        'paypal',
        'IPN object flagged for donation {0} ({1})'.format(donation.id, ipn.txn_id),
        event=donation.event,
    )
    donation.save()


def get_paypal_donation(paypalemail, amount, transactionid):
    donations = Donation.objects.filter(
        amount=amount, domain='PAYPAL', domainId=transactionid
    )
    if donations.exists():
        donation = donations[0]
        donors = Donor.objects.filter(paypalemail=paypalemail)
        if donors.exists() and donation.donor.id == donors[0].id:
            return donation
    return None


_reasonCodeDetails = {
    'echeck': (
        'Payments sent as eCheck tend to take several days to a week to clear. Unfortunately, there is nothing we can do to expedite this process. In the future, please consider using an instant payment.',
        False,
    ),
    'paymentreview': (
        'The payment is being reviewed by PayPal. Typically, this will occur with large transaction amounts and/or from accounts with low overall activity.',
        False,
    ),
    'regulatory_review': (
        'This payment is being reviewed for compliance with government regulations.',
        False,
    ),
    'intl': (
        'The payment was sent via a currency the target account is not set up to receive, and must be confirmed manually by the account holder.',
        True,
    ),
    'multi-currency': (
        'The payment was sent in a currency the target account cannot convert from, and must be manually converted by the account holder.',
        True,
    ),
    'unilateral': ('The receiver account e-mail has not yet been confirmed', True),
    'upgrade': (
        'The receiver account is unable to process the payment, due to its account status',
        True,
    ),
}


def get_pending_reason_details(pending_reason):
    return _reasonCodeDetails.get(pending_reason, ('', True))


def log_ipn(ipnObj, message=''):
    donation = get_ipn_donation(ipnObj)
    message = '{message}\ntxn_id : {txn_id}\nstatus : {status}\nemail : {email}\namount : {amount}\ndate : {date}\ncustom : {custom}\ndonation : {donation}'.format(
        **{
            'message': message,
            'txn_id': ipnObj.txn_id,
            'status': ipnObj.payment_status,
            'email': ipnObj.payer_email,
            'amount': ipnObj.mc_gross,
            'date': ipnObj.payment_date,
            'custom': ipnObj.custom,
            'donation': donation,
        }
    )
    status = ipnObj.payment_status.lower()
    if status == 'pending':
        message += 'pending : ' + ipnObj.pending_reason
    elif status in ['reversed', 'refunded', 'canceled_reversal', 'denied']:
        message += 'reason  : ' + ipnObj.reason_code
    viewutil.tracker_log('paypal', message, event=donation.event if donation else None)


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


# Fired when the payment processor tells us that the donation cannot yet
# be confirmed, for any reason.
def _track_donation_pending(donation, ipn, receivers_fault):
    analytics.track(
        AnalyticsEventTypes.DONATION_PENDING,
        {
            **_get_donation_event_fields(donation),
            'timestamp': datetime.datetime.utcnow(),
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
            'timestamp': datetime.datetime.utcnow(),
        },
    )


# Fired when the donation is cancelled or reversed through the payment processor.
def _track_donation_cancelled(donation):
    analytics.track(
        AnalyticsEventTypes.DONATION_CANCELLED,
        {
            **_get_donation_event_fields(donation),
            'timestamp': datetime.datetime.utcnow(),
        },
    )
