import logging
import traceback
from decimal import Decimal

import post_office.mail
from django.conf import settings
from django.dispatch import receiver
from paypal.standard.ipn.signals import valid_ipn_received, invalid_ipn_received
from tracker import viewutil, tasks
from tracker.models import Country, Donation, Donor, DonorPayPalIPNInfo

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
    recipient_email = ipn.business or ipn.receiver_email
    if recipient_email.lower() != email.lower():
        raise SpoofedIPNException(f"IPN receiver %s doesn't match %s")


def get_ipn_donation(ipn_obj):
    if ipn_obj.custom:
        try:
            return Donation.objects.filter(pk=int(ipn_obj.custom.split(':')[0])).first()
        except ValueError:
            logger.warning(
                f'Unknown custom field for IPN #{ipn_obj.id}: {ipn_obj.custom!r}'
            )
    return None


@receiver(valid_ipn_received)
def valid_ipn(sender, **kwargs):
    try:
        donation = get_ipn_donation(sender)

        if not donation:
            viewutil.tracker_log('paypal', f'No donation found for IPN {sender.txn_id}')
            return

        verify_ipn_recipient_email(
            sender, donation.event.paypal_ipn_settings.receiver_email
        )

        donor_ipn_info = DonorPayPalIPNInfo.objects.filter(
            payer_id=sender.payer_id
        ).first()
        if not donor_ipn_info:
            donor_ipn_info = DonorPayPalIPNInfo.objects.filter(
                payer_email=sender.payer_email,
                payer_verified=sender.payer_status == 'verified',
            ).first()
        if not donor_ipn_info:
            donor_ipn_info = DonorPayPalIPNInfo.objects.create(
                donor=Donor.objects.create(
                    email=sender.payer_email.lower(), visibility='ANON'
                ),
                payer_id=sender.payer_id,
                payer_email=sender.payer_email,
                payer_verified=sender.payer_status == 'verified',
            )
        donor_ipn_info.payer_id = sender.payer_id
        donor_ipn_info.payer_email = sender.payer_email
        # can maybe go from unverified to verified if the payer_id is stable,
        # but not sure about the other direction? probably a degenerate case at best
        donor_ipn_info.payer_verified = sender.payer_status == 'verified'
        donor_ipn_info.save()
        donor = donor_ipn_info.donor

        donor.firstname = sender.first_name
        donor.lastname = sender.last_name
        donor.addressstreet = sender.address_street
        donor.addresscity = sender.address_city
        donor.addresscountry = Country.objects.get(
            alpha2=(sender.residence_country or sender.address_country_code)
        )
        donor.addressstate = sender.address_state
        donor.addresszip = sender.address_zip
        donor.save()

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
        donation.domainId = sender.txn_id
        donation.donor = donor
        donation.amount = Decimal(sender.mc_gross)
        donation.currency = sender.mc_currency
        if not donation.timereceived:
            donation.timereceived = sender.payment_date
        donation.testdonation = sender.test_ipn
        donation.fee = Decimal(sender.mc_fee or 0)

        # if the cleared amount was less that the total amount for allocated bids, remove them all
        # might be a sign of tampering, or some other weirdness, log the amounts removed
        # very edge-case but still worth checking for
        bid_total = sum(b.amount for b in donation.bids.all())
        if bid_total > sender.mc_gross:
            log_message = f'Cleared total was less than sum of bids: {bid_total} > {sender.mc_gross}, removed all bids'
            for bid in donation.bids.all():
                log_message += f'\nBid #{bid.bid.id}: {bid.amount}'
            donation.modcomment += f'\n***\n{log_message}'
            donation.bids.all().delete()
            viewutil.tracker_log(
                'paypal',
                f'Donation #{donation.id}: {log_message}',
                event=donation.event,
            )

        payment_status = sender.payment_status.lower()

        if payment_status == 'pending':
            donation.transactionstate = 'PENDING'
        elif (
            payment_status == 'completed'
            or payment_status == 'canceled_reversal'
            or payment_status == 'processed'
        ):
            donation.transactionstate = 'COMPLETED'
        elif (
            payment_status == 'refunded'
            or payment_status == 'reversed'
            or payment_status == 'failed'
            or payment_status == 'voided'
            or payment_status == 'denied'
        ):
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

        if donation.transactionstate == 'PENDING':
            reason_explanation, our_fault = get_pending_reason_details(
                sender.pending_reason
            )
            if donation.event.pendingdonationemailtemplate:
                format_context = {
                    'event': donation.event,
                    'donation': donation,
                    'donor': donation.donor,
                    'pending_reason': sender.pending_reason,
                    'reason_info': reason_explanation if not our_fault else '',
                }
                post_office.mail.send(
                    recipients=[donation.donor.email],
                    sender=donation.event.donationemailsender,
                    template=donation.event.pendingdonationemailtemplate,
                    context=format_context,
                )
            # some pending reasons can be a problem with the receiver account, we should keep track of them
            if our_fault:
                logger.warning(f'Unhandled pending error: {sender.pending_reason}')
                log_ipn(sender, 'Unhandled pending error')
        elif donation.transactionstate == 'COMPLETED':
            if donation.event.donationemailtemplate is not None:
                format_context = {
                    'donation': donation,
                    'donor': donation.donor,
                    'event': donation.event,
                    'prizes': viewutil.get_donation_prize_info(donation),
                }
                post_office.mail.send(
                    recipients=[donation.donor.email],
                    sender=donation.event.donationemailsender,
                    template=donation.event.donationemailtemplate,
                    context=format_context,
                )
            if getattr(settings, 'HAS_CELERY', False):
                tasks.post_donation_to_postbacks.delay(donation.id)
            else:
                tasks.post_donation_to_postbacks(donation.id)

        elif donation.transactionstate == 'CANCELLED':
            # eventually we may want to send out e-mail for some of the possible cases
            # such as payment reversal due to double-transactions (this has happened before)
            log_ipn(sender, 'Cancelled/reversed payment')

    except Exception as exc:
        # just to make sure we have a record of it somewhere
        logger.exception('Exception while processing IPN')
        log_ipn(
            sender, f'{exc} \n {traceback.format_exc()}',
        )


@receiver(invalid_ipn_received)
def invalid_ipn(sender, **kwargs):
    error_message = f'Invalid IPN received: {sender.flag_info}'
    donation = get_ipn_donation(sender)
    if donation:
        donation.transactionstate = 'FLAGGED'
        donation.save()
        viewutil.tracker_log(
            'paypal',
            'IPN object flagged for donation {0} ({1})'.format(
                donation.id, sender.txn_id
            ),
            event=donation.event,
        )
    logger.error(error_message)
    viewutil.tracker_log(
        'paypal', error_message,
    )


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


def log_ipn(ipn_obj, message=''):
    donation = get_ipn_donation(ipn_obj)
    message = '{message}\ntxn_id : {txn_id}\nstatus : {status}\nemail : {email}\namount : {amount}\ndate : {date}\ncustom : {custom}\ndonation : {donation}'.format(
        **{
            'message': message,
            'txn_id': ipn_obj.txn_id,
            'status': ipn_obj.payment_status,
            'email': ipn_obj.payer_email,
            'amount': ipn_obj.mc_gross,
            'date': ipn_obj.payment_date,
            'custom': ipn_obj.custom,
            'donation': donation,
        }
    )
    status = ipn_obj.payment_status.lower()
    if status == 'pending':
        message += 'pending : ' + ipn_obj.pending_reason
    elif status in ['reversed', 'refunded', 'canceled_reversal', 'denied']:
        message += 'reason  : ' + ipn_obj.reason_code
    viewutil.tracker_log('paypal', message, event=donation.event if donation else None)
