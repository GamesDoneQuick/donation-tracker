from paypal.standard.ipn.forms import PayPalIPNForm
from paypal.standard.ipn.models import PayPalIPN
from tracker.models import *
from datetime import *
import random

from decimal import *
import pytz

def initialize_ipn_object(request):
  flag = None
  ipn_obj = None
  form = PayPalIPNForm(request.POST)
  if form.is_valid():
    try:
      ipn_obj = form.save(commit=False)
    except Exception, e:
      flag = "Exception while processing. (%s)" % e
  else:
    flag = "Invalid form. (%s)" % form.errors
  if ipn_obj is None:
    ipn_obj = PayPalIPN()
  ipn_obj.initialize(request)
  if flag is not None:
    ipn_obj.set_flag(flag)
  return ipn_obj

def initialize_paypal_donation(donation, ipnObj):
  defaults = {
    'email'           : ipnObj.payer_email.lower(),
    'firstname'       : ipnObj.first_name,
    'lastname'        : ipnObj.last_name,
    'address_street'  : ipnObj.address_street,
    'address_city'    : ipnObj.address_city,
    'address_country' : ipnObj.address_country,
    'address_state'   : ipnObj.address_state,
    'address_zip'     : ipnObj.address_zip,
    'visibility'      : 'ANON',
  }
  donor = Donor.objects.get_or_create(paypalemail=ipnObj.payer_email.lower(),defaults=defaults)

  if donation:
    if donation.requestedvisibility != 'CURR':
      donor.visibility = donation.requestedvisibility
    if donation.requestedalias and (not donor.alias or donation.requestedalias.lower() != donor.alias.lower()):
      foundAResult = False
      currentAlias = donation.requestedalias
      while not foundAResult:
        results = Donor.objects.filter(alias__iexact=currentAlias)
        if results.exists():
          currentAlias = donation.requestedalias + str(random.getrandbits(4))
        else:
          foundAResult = True
      donor.alias = currentAlias
    if donation.requestedemail and donation.requestedemail != donor.email and not Donor.objects.filter(email=donation.requestedemail).exists():
      donor.email = donation.requestedemail
  donor.save()

  if not donation:
    donation = Donation.objects.create()

  donation.domain='PAYPAL'
  donation.domainId=ipnObj.txn_id
  donation.donor=donor
  donation.amount=Decimal(ipnObj.mc_gross)
  donation.currency=ipnObj.mc_currency
  if not donation.timereceived:
    donation.timereceived = datetime.utcnow()
  donation.testdonation=ipnObj.test_ipn
  donation.fee=Decimal(ipnObj.mc_fee or 0)
  donation.event = Event.objects.all().order_by('-date')[0]

  # if the user attempted to tamper with the donation amount, remove all bids
  if donation.amount != ipnObj.mc_gross:
    donation.modcomment += u"\n*Tampered donation amount from " + str(donation.amount) + u" to " + str(ipnObj.mc_gross) + u", removed all bids*"
    donation.amount = ipnObj.mc_gross
    donation.choicebid_set.clear()
    donation.challengebid_set.clear()

  if not ipnObj.flag and ipnObj.payment_status.lower() in ['completed', 'refunded']:
    if ipnObj.payment_status.lower() == 'completed':
      donation.transactionstate = 'COMPLETED'
    elif ipnObj.payment_status.lower() == 'refunded':
      donation.transactionstate = 'CANCELLED'
  donation.save()
  # I think we only care if the _donation_ was freshly created
  return donation

def get_paypal_donation(paypalemail, amount, transactionid):
  donations = Donation.objects.filter(amount=amount, domain='PAYPAL', domainId=transactionid)
  if donations.exists():
    donation = donations[0]
    donors = Donor.objects.filter(paypalemail=paypalemail)
    if donors.exists() and donation.donor.id == donors[0].id:
      return donation
  return None

