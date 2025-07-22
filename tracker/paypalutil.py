import contextlib
import datetime
import logging
import re
from decimal import Decimal
from typing import Optional

import post_office
from django.core.signing import BadSignature, Signer
from django.db.models.signals import post_save
from django.dispatch import receiver
from paypal.standard.ipn.models import PayPalIPN
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


def _get_gross(ipn):
    gross = ipn.mc_gross
    # for some reason these show up with adjusted `mc_gross` fields, so compensate for that
    if ipn.payment_status.lower() == 'canceled_reversal':
        gross += ipn.mc_fee
    return gross


def get_ipn_donation(
    ipn: PayPalIPN,
    *,
    prefix: Optional[str] = None,
    allow_old_format: Optional[bool] = None,
    fallback_keys: Optional[list[str]] = None,
) -> Optional[Donation]:
    """
    historically, there are three formats for the custom field on an incoming IPN

    - event id only, used only for the initial 2013 implementation, so if we're reprocessing this then the domainId should
      match the transaction id, as there is no other way to verify the link.
    - `{donation.id}:{donation.domainId}`, where the initial domainId is a nonce. After the initial IPN is received, any
      further IPNs regarding the same donation should match that nonce. These could still theoretically be coming in
      after a code upgrade. Most successful transactions resolve within 5 minutes, and even e-checks only take a couple
      of weeks in practice. Anything beyond that is chargeback/refunds. The longest delay I (BC) have recorded as of
      May 2025 is 6 months, but that is an EXTREME outlier involving back-and-forth with a chargeback.
    - `{prefix}:{donation.id}:{signature}`, where `prefix` is `settings.TRACKER_PAYPAL_SIGNATURE_PREFIX` and `signature` is
      a signed JSON dictionary with, at minimum, an `id` key that needs to match, and salted with the donation amount (to
      further detect tampering or other bugs). Usually generated by `Donation.paypal_signature`.

    Unless `settings.TRACKER_PAYPAL_ALLOW_OLD_IPN_FORMAT` is true, only the third is recognized by this function. The
    signature block must pass verification using either `settings.SECRET_KEY` or one of the keys in
    `settings.SECRET_KEY_FALLBACKS`. These settings, plus the expected prefix, can be overridden via keyword arguments.
    """
    prefix = prefix if prefix is not None else settings.TRACKER_PAYPAL_SIGNATURE_PREFIX
    allow_old_format = (
        allow_old_format
        if allow_old_format is not None
        else settings.TRACKER_PAYPAL_ALLOW_OLD_IPN_FORMAT
    )
    fallback_keys = (
        fallback_keys if fallback_keys is not None else settings.SECRET_KEY_FALLBACKS
    )
    parts = ipn.custom.split(':', maxsplit=2)
    pk = None
    if parts[0] == prefix and len(parts) == 3:
        try:
            # salting with the amount also ensures that the form was not tampered with in that manner
            obj = Signer(
                salt=str(_get_gross(ipn)), fallback_keys=fallback_keys
            ).unsign_object(parts[2])
            if not isinstance(obj, dict) or str(obj.get('id', None)) != parts[1]:
                raise BadSignature
        except BadSignature:
            viewutil.tracker_log(
                'paypal', f'Invalid or expired signature on IPN #`{ipn.id}`.'
            )
            return None
        pk = parts[1]
    elif allow_old_format:
        if len(parts) == 2:  # `{donation.id}:{donation.domainId}` format
            pk = parts[0]
            first = PayPalIPN.objects.filter(custom__startswith=f'{pk}:').first()
            if first is None or first.custom != ipn.custom:
                viewutil.tracker_log('paypal', f'V2 custom block mismatch. #`{ipn.id}`')
                return None
        elif len(parts) == 1 and re.match(
            r'^\d+$', parts[0]
        ):  # might be `{event.id}` format
            donation = Donation.objects.filter(
                event=parts[0], domain='PAYPAL', domainId=ipn.txn_id
            ).first()
            if donation is None:
                viewutil.tracker_log(
                    'paypal',
                    f'IPN appears to be 2013 style, but txn_id did not match. #`{ipn.id}`',
                )
            return donation
    if pk is None:
        viewutil.tracker_log(
            'paypal',
            f'Not processing IPN due to unrecognized format, disabled legacy format, or incorrect prefix. #`{ipn.id}`',
        )
        return None
    with contextlib.suppress(ValueError):
        pk = int(pk)
        donation = Donation.objects.filter(pk=pk).prefetch_related('ipns').first()
        # log a couple of pathological cases because they probably indicate a programming error, or the form
        # got corrupted and cannot be trusted
        if donation:
            if donation.domain != 'PAYPAL':
                viewutil.tracker_log(
                    'paypal', f'Donation is not from PayPal. #`{ipn.id}`'
                )
                return None
            elif donation.amount != _get_gross(ipn):
                viewutil.tracker_log('paypal', f'Donation amount mismatch. #`{ipn.id}`')
                return None
            try:
                verify_ipn_recipient_email(ipn, donation.event.paypalemail)
            except SpoofedIPNException:
                viewutil.tracker_log('paypal', f'Recipient email mismatch. #`{ipn.id}`')
                return None
            return donation
    return None


def _fill_donor_address(donor, ipn):
    if not donor.addressstreet:
        donor.addressstreet = ipn.address_street
    if not donor.addresscity:
        donor.addresscity = ipn.address_city
    if not donor.addresscountry:
        countrycode = (
            ipn.residence_country
            if not ipn.address_country_code
            else ipn.address_country_code
        )
        donor.addresscountry = Country.objects.filter(alpha2=countrycode).first()
    if not donor.addressstate:
        donor.addressstate = ipn.address_state
    if not donor.addresszip:
        donor.addresszip = ipn.address_zip
    donor.save()


@receiver(valid_ipn_received)
def initialize_paypal_donation(sender, **kwargs):
    ipn = sender
    donation = get_ipn_donation(ipn)

    if donation is None:
        return

    if donation.event.archived:
        # could be a delayed chargeback or similar
        viewutil.tracker_log(
            'paypal', f'IPN on archived event, but processing anyway. #`{ipn.id}`.'
        )

    defaults = {
        'email': ipn.payer_email.lower(),
        'firstname': ipn.first_name,
        'lastname': ipn.last_name,
        'visibility': 'ANON',
    }
    donor, created = Donor.objects.get_or_create(
        paypalemail=ipn.payer_email.lower(), defaults=defaults
    )

    _fill_donor_address(donor, ipn)

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

    payment_status = ipn.payment_status.lower()

    if payment_status == 'pending':
        donation.transactionstate = 'PENDING'
    elif (
        payment_status == 'completed'
        or payment_status == 'canceled_reversal'
        or payment_status == 'processed'
    ):
        if donation.cleared_at is None:
            donation.cleared_at = ipn.created_at
        donation.transactionstate = 'COMPLETED'
    elif (
        payment_status == 'refunded'
        or payment_status == 'reversed'
        or payment_status == 'failed'
        or payment_status == 'voided'
        or payment_status == 'denied'
    ):
        donation.cleared_at = None
        donation.transactionstate = 'CANCELLED'
    else:
        donation.transactionstate = 'FLAGGED'
        viewutil.tracker_log(
            'paypal',
            'Unknown payment status in donation {0} ({1})'.format(
                donation.id, payment_status
            ),
            event=donation.event,
        )

    donation.save()

    if donation.transactionstate == 'COMPLETED':
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
        if settings.TRACKER_HAS_CELERY:
            tasks.post_donation_to_postbacks.delay(donation.id)
        else:
            tasks.post_donation_to_postbacks(donation.id)
        _track_donation_completed(donation)
    elif donation.transactionstate == 'PENDING':
        reasonExplanation, ourFault = _get_pending_reason_details(ipn.pending_reason)
        if donation.event.pendingdonationemailtemplate:
            formatContext = {
                'event': donation.event,
                'donation': donation,
                'donor': donation.donor,
                'pending_reason': ipn.pending_reason,
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
            _log_ipn(ipn, 'Unhandled pending error')

        _track_donation_pending(donation, ipn, ourFault)
    elif donation.transactionstate == 'CANCELLED':
        # eventually we may want to send out e-mail for some of the possible cases
        # such as payment reversal due to double-transactions (this has happened before)
        _log_ipn(ipn, 'Cancelled/reversed payment')
        _track_donation_cancelled(donation)


@receiver(invalid_ipn_received)
def handle_ipn_error(*, sender, **kwargs):
    ipn = sender

    # this is harmless
    if 'Duplicate txn_id.' in ipn.flag_info:
        return

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


def _get_paypal_donation(paypalemail, amount, transactionid):
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


def _get_pending_reason_details(pending_reason):
    return _reasonCodeDetails.get(pending_reason, ('', True))


def _log_ipn(ipn, message=''):
    donation = get_ipn_donation(ipn)
    message = '{message}\ntxn_id : {txn_id}\nstatus : {status}\nemail : {email}\namount : {amount}\ndate : {date}\ncustom : {custom}\ndonation : {donation}'.format(
        **{
            'message': message,
            'txn_id': ipn.txn_id,
            'status': ipn.payment_status,
            'email': ipn.payer_email,
            'amount': ipn.mc_gross,
            'date': ipn.payment_date,
            'custom': ipn.custom,
            'donation': donation,
        }
    )
    status = ipn.payment_status.lower()
    if status == 'pending':
        message += 'pending : ' + ipn.pending_reason
    elif status in ['reversed', 'refunded', 'canceled_reversal', 'denied']:
        message += 'reason  : ' + ipn.reason_code
    viewutil.tracker_log('paypal', message, event=donation.event if donation else None)


@receiver(post_save, sender=PayPalIPN)
def donation_ipns_update(sender, instance, created, raw, **kwargs):
    if d := (
        get_ipn_donation(instance)
        or Donation.objects.filter(domain='PAYPAL', domainId=instance.txn_id).first()
    ):
        d.ipns.add(instance)
