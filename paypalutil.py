from paypal.standard.ipn.forms import PayPalIPNForm;
from paypal.standard.ipn.models import PayPalIPN;
from tracker.models import *;

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

def auto_create_paypal_donation(ipnObj, event):
  donor, created = Donor.objects.get_or_create(email=ipnObj.payer_email.lower())
  if created:
    donor.firstname = ipnObj.first_name;
    donor.lastname = ipnObj.last_name;
    donor.address_street = ipnObj.address_street;
    donor.address_city = ipnObj.address_city;
    donor.address_country = ipnObj.address_country;
    donor.address_state = ipnObj.address_state;
    donor.address_zip = ipnObj.address_zip;
    donor.save();
  # I'm pretty sure paypal exclusively reports times in PST/PDT, so this code is safe
  paypaltz = pytz.timezone('America/Los_Angeles')
  utcTimeReceived = paypaltz.normalize(ipnObj.payment_date.replace(tzinfo=paypaltz));
  utcTimeReceived = utcTimeReceived.astimezone(pytz.utc);
  donation, created = Donation.objects.get_or_create(domain='PAYPAL', domainId=ipnObj.txn_id, event=event, donor=donor, amount=Decimal(ipnObj.mc_gross), timereceived=utcTimeReceived, testdonation=ipnObj.test_ipn, fee=Decimal(ipnObj.mc_fee));
  # I think we only care if the _donation_ was freshly created
  return donation, created;

def get_paypal_donation(paypalemail, amount, transactionid):
  donations = Donation.objects.filter(amount=amount, domain='PAYPAL', domainId=transactionid);
  if donations.exists():
    donation = donations[0];
    donors = Donor.objects.filter(email=paypalemail);
    if donors.exists() and donation.donor.id == donors[0].id:
      return donation;
  return None;

