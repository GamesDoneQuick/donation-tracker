from paypal.standard.ipn.forms import PayPalIPNForm;
from paypal.standard.ipn.models import PayPalIPN;
from tracker.models import *;
from datetime import *;
import random;

from decimal import *;
import pytz;

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
  return ipn_obj;

def initialize_paypal_donation(donation, ipnObj):
  donor, created = Donor.objects.get_or_create(paypalemail=ipnObj.payer_email.lower())
  if created:
    donor.email = ipnObj.payer_email.lower();
    donor.firstname = ipnObj.first_name;
    donor.lastname = ipnObj.last_name;
    donor.address_street = ipnObj.address_street;
    donor.address_city = ipnObj.address_city;
    donor.address_country = ipnObj.address_country;
    donor.address_state = ipnObj.address_state;
    donor.address_zip = ipnObj.address_zip;
    donor.visibility = 'ANON';
  if donation:
    if donation.requestedvisibility != 'CURR':
      donor.visibility = donation.requestedvisibility;
    if donation.requestedalias and (not donor.alias or donation.requestedalias.lower() != donor.alias.lower()):
      foundAResult = False;
      currentAlias = donation.requestedalias;
      while not foundAResult:
        results = Donor.objects.filter(alias__iexact=currentAlias);
        if results.exists():
          currentAlias = donation.requestedalias + str(random.getrandbits(128));
        else:
          foundAResult = True;
      donor.alias = currentAlias;
    if donation.requestedemail and donation.requestedemail != donor.email and not Donor.objects.filter(email=donation.requestedemail).exists():
      donor.email = donation.requestedemail;
  donor.save();
  # I'm pretty sure paypal exclusively reports times in PST/PDT, so this code is safe
  #paypaltz = pytz.timezone('America/Los_Angeles')
  #utcTimeReceived = paypaltz.normalize(paypaltz.localize(ipnObj.payment_date));
  #utcTimeReceived = utcTimeReceived.astimezone(pytz.utc);
  if not donation:
    donation = Donation.objects.create();
    
  donation.domain='PAYPAL';
  donation.domainId=ipnObj.txn_id;
  donation.donor=donor;
  donation.amount=Decimal(ipnObj.mc_gross);
  donation.currency=ipnObj.mc_currency;
  #donation.timereceived=utcTimeReceived
  donation.testdonation=ipnObj.test_ipn;
  donation.fee=Decimal(ipnObj.mc_fee);

  # if the user attempted to tamper with the donation amount, remove all bids
  if donation.amount != ipnObj.mc_gross:
    donation.modcomment += "\n*Tampered donation amount from " + str(donation.amount) + " to " + str(ipnObj.mc_gross) + ", removed all bids*"; 
    donation.amount = ipnObj.mc_gross;
    donation.choicebid_set.clear();
    donation.challengebid_set.clear();

  if not ipnObj.flag and ipnObj.payment_status.lower() in ['completed', 'refunded']:
    if ipnObj.payment_status.lower() == 'completed':
      donation.transactionstate = 'COMPLETED';
    elif ipnObj.payment_status.lower() == 'refunded':
      donation.transactionstate = 'CANCELLED';
  donation.save();
  # I think we only care if the _donation_ was freshly created
  return donation;

def get_paypal_donation(paypalemail, amount, transactionid):
  donations = Donation.objects.filter(amount=amount, domain='PAYPAL', domainId=transactionid);
  if donations.exists():
    donation = donations[0];
    donors = Donor.objects.filter(paypalemail=paypalemail);
    if donors.exists() and donation.donor.id == donors[0].id:
      return donation;
  return None;

