from paypal.standard.ipn.forms import PayPalIPNForm
from paypal.standard.ipn.models import PayPalIPN
from tracker.models import Country, Donation, Event, Donor
from datetime import datetime
import tracker.viewutil as viewutil
import random

from decimal import Decimal


class SpoofedIPNException(Exception):
    pass


def create_ipn(request):
    flag = None
    ipn = None
    form = PayPalIPNForm(request.POST)
    if form.is_valid():
        try:
            ipn = form.save(commit=False)
        except Exception as e:
            flag = 'Exception while processing. (%s)' % e
    else:
        flag = 'Invalid form. (%s)' % form.errors
    if ipn is None:
        ipn = PayPalIPN()
    ipn.initialize(request)
    if flag is not None:
        ipn.set_flag(flag)
    else:
        # Secrets should only be used over SSL.
        if request.is_secure() and 'secret' in request.GET:
            ipn.verify_secret(form, request.GET['secret'])
        else:
            donation = get_ipn_donation(ipn)
            if not donation:
                raise Exception('No donation associated with this IPN')
            ipn.verify()
            verify_ipn_recipient_email(ipn, donation.event.paypalemail)
    ipn.save()
    return ipn


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


def get_ipn(request):
    ipn = PayPalIPN()
    ipn.initialize(request)
    return ipn


def get_ipn_donation(ipn):
    if ipn.custom:
        toks = ipn.custom.split(':')
        pk = int(toks[0])
        return Donation.objects.filter(pk=pk).first()
    else:
        return None


def fill_donor_address(donor, ipn):
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
        donor.addresscountry = Country.objects.get(alpha2=countrycode)
    if not donor.addressstate:
        donor.addressstate = ipn.address_state
    if not donor.addresszip:
        donor.addresszip = ipn.address_zip
    donor.save()


def initialize_paypal_donation(ipn):
    countrycode = (
        ipn.residence_country
        if not ipn.address_country_code
        else ipn.address_country_code
    )
    defaults = {
        'email': ipn.payer_email.lower(),
        'firstname': ipn.first_name,
        'lastname': ipn.last_name,
        'addressstreet': ipn.address_street,
        'addresscity': ipn.address_city,
        'addresscountry': Country.objects.get(alpha2=countrycode),
        'addressstate': ipn.address_state,
        'addresszip': ipn.address_zip,
        'visibility': 'ANON',
    }
    donor, created = Donor.objects.get_or_create(
        paypalemail=ipn.payer_email.lower(), defaults=defaults
    )

    fill_donor_address(donor, ipn)

    donation = get_ipn_donation(ipn)

    if donation:
        if donation.requestedvisibility != 'CURR':
            donor.visibility = donation.requestedvisibility
        if donation.requestedalias and (
            not donor.alias or donation.requestedalias.lower() != donor.alias.lower()
        ):
            found_result = False
            current_alias = donation.requestedalias
            while not found_result:
                results = Donor.objects.filter(alias__iexact=current_alias)
                if results.exists():
                    current_alias = donation.requestedalias + str(random.getrandbits(8))
                else:
                    found_result = True
            donor.alias = current_alias
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
    donation.domainId = ipn.txn_id
    donation.donor = donor
    donation.amount = Decimal(ipn.mc_gross)
    donation.currency = ipn.mc_currency
    if not donation.timereceived:
        donation.timereceived = datetime.utcnow()
    donation.testdonation = ipn.test_ipn
    donation.fee = Decimal(ipn.mc_fee or 0)

    # if the user attempted to tamper with the donation amount, remove all bids
    if donation.amount != ipn.mc_gross:
        donation.modcomment += (
            '\n*Tampered donation amount from '
            + str(donation.amount)
            + ' to '
            + str(ipn.mc_gross)
            + ', removed all bids*'
        )
        donation.amount = ipn.mc_gross
        donation.bids.clear()
        viewutil.tracker_log(
            'paypal',
            'Tampered amount detected in donation {0} (${1} -> ${2})'.format(
                donation.id, donation.amount, ipn.mc_gross
            ),
            event=donation.event,
        )

    payment_status = ipn.payment_status.lower()

    if not ipn.flag:
        if payment_status == 'pending':
            donation.transactionstate = 'PENDING'
        elif payment_status in ['completed', 'canceled_reversal', 'processed']:
            donation.transactionstate = 'COMPLETED'
        elif payment_status in ['refunded', 'reversed', 'failed', 'voided', 'denied']:
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
    else:
        donation.transactionstate = 'FLAGGED'
        viewutil.tracker_log(
            'paypal',
            'IPN object flagged for donation {0} ({1})'.format(donation.id, ipn.txn_id),
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


REASON_CODE_DETAILS = {
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
    return REASON_CODE_DETAILS.get(pending_reason, ('', True))


def log_ipn(ipn, message=''):
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
