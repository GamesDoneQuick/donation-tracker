import logging
import traceback
from datetime import datetime
from decimal import Decimal

import post_office.mail
from django.dispatch import receiver
from paypal.standard.ipn.signals import valid_ipn_received, invalid_ipn_received
from tracker import viewutil, eventutil
from tracker.models import Country, Donation, Event, Donor

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
            "IPN receiver %s doesn't match %s".format(recipient_email, email)
        )


def get_ipn_donation(ipn_obj):
    if ipn_obj.custom:
        toks = ipn_obj.custom.split(':')
        pk = int(toks[0])
        return Donation.objects.filter(pk=pk).first()
    else:
        return None


def fill_donor_address(donor, ipn_obj):
    if not donor.addressstreet:
        donor.addressstreet = ipn_obj.address_street
    if not donor.addresscity:
        donor.addresscity = ipn_obj.address_city
    if not donor.addresscountry:
        countrycode = (
            ipn_obj.residence_country
            if not ipn_obj.address_country_code
            else ipn_obj.address_country_code
        )
        donor.addresscountry = Country.objects.get(alpha2=countrycode)
    if not donor.addressstate:
        donor.addressstate = ipn_obj.address_state
    if not donor.addresszip:
        donor.addresszip = ipn_obj.address_zip
    donor.save()


@receiver(valid_ipn_received)
def valid_ipn(ipn_obj):
    try:
        donation = initialize_paypal_donation(ipn_obj)

        if donation.transactionstate == 'PENDING':
            reason_explanation, our_fault = get_pending_reason_details(
                ipn_obj.pending_reason
            )
            if donation.event.pendingdonationemailtemplate:
                format_context = {
                    'event': donation.event,
                    'donation': donation,
                    'donor': donation.donor,
                    'pending_reason': ipn_obj.pending_reason,
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
                log_ipn(ipn_obj, 'Unhandled pending error')
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
            eventutil.post_donation_to_postbacks(donation)

        elif donation.transactionstate == 'CANCELLED':
            # eventually we may want to send out e-mail for some of the possible cases
            # such as payment reversal due to double-transactions (this has happened before)
            log_ipn(ipn_obj, 'Cancelled/reversed payment')

    except Exception as inst:
        # just to make sure we have a record of it somewhere
        logger.exception('Exception while processing IPN')
        log_ipn(
            ipn_obj, f'{inst} \n {traceback.format_exc()}',
        )


@receiver(invalid_ipn_received)
def invalid_ipn(ipn_obj):
    error_message = f'Invalid IPN received: {ipn_obj.flag_info}'
    donation = get_ipn_donation(ipn_obj)
    if donation:
        donation.transactionstate = 'FLAGGED'
        donation.save()
        viewutil.tracker_log(
            'paypal',
            'IPN object flagged for donation {0} ({1})'.format(
                donation.id, ipn_obj.txn_id
            ),
            event=donation.event,
        )
    logger.error(error_message)
    viewutil.tracker_log(
        'paypal', error_message,
    )


def initialize_paypal_donation(ipn_obj):
    countrycode = (
        ipn_obj.residence_country
        if not ipn_obj.address_country_code
        else ipn_obj.address_country_code
    )
    defaults = {
        'email': ipn_obj.payer_email.lower(),
        'firstname': ipn_obj.first_name,
        'lastname': ipn_obj.last_name,
        'addressstreet': ipn_obj.address_street,
        'addresscity': ipn_obj.address_city,
        'addresscountry': Country.objects.get(alpha2=countrycode),
        'addressstate': ipn_obj.address_state,
        'addresszip': ipn_obj.address_zip,
        'visibility': 'ANON',
    }
    donor, created = Donor.objects.get_or_create(
        paypalemail=ipn_obj.payer_email.lower(), defaults=defaults
    )

    fill_donor_address(donor, ipn_obj)

    donation = get_ipn_donation(ipn_obj)

    if donation:
        verify_ipn_recipient_email(
            ipn_obj, donation.event.paypal_ipn_settings.receiver_email
        )

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
    else:
        donation = Donation()
        donation.modcomment = '*Donation for ipn was not found, creating new*'
        donation.event = Event.objects.latest()

    donation.domain = 'PAYPAL'
    donation.domainId = ipn_obj.txn_id
    donation.donor = donor
    donation.amount = Decimal(ipn_obj.mc_gross)
    donation.currency = ipn_obj.mc_currency
    if not donation.timereceived:
        donation.timereceived = datetime.utcnow()
    donation.testdonation = ipn_obj.test_ipn
    donation.fee = Decimal(ipn_obj.mc_fee or 0)

    # if the user attempted to tamper with the donation amount, remove all bids
    if donation.amount != ipn_obj.mc_gross:
        donation.modcomment += (
            '\n*Tampered donation amount from '
            + str(donation.amount)
            + ' to '
            + str(ipn_obj.mc_gross)
            + ', removed all bids*'
        )
        donation.amount = ipn_obj.mc_gross
        donation.bids.all().delete()
        viewutil.tracker_log(
            'paypal',
            'Tampered amount detected in donation {0} (${1} -> ${2})'.format(
                donation.id, donation.amount, ipn_obj.mc_gross
            ),
            event=donation.event,
        )

    payment_status = ipn_obj.payment_status.lower()

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

    # Automatically approve anonymous, no-comment donations if an auto-approve
    # threshold is set.
    auto_min = donation.event.auto_approve_threshold
    if auto_min:
        donation.approve_if_anonymous_and_no_comment(auto_min)

    donation.save()
    # I think we only care if the _donation_ was freshly created
    return donation


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
