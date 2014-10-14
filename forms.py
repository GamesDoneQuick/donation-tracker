from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from tracker import models
from tracker.validators import *
import paypal
import re
from decimal import *
from django.forms import formsets
import django.core.exceptions

import tracker.fields
import tracker.widgets

__all__ = [
	'UsernameForm',
	'DonationCredentialsForm',
	'DonationEntryForm',
	'DonationBidForm',
	'DonationBidFormSet',
	'DonationSearchForm',
	'BidSearchForm',
	'PrizeTicketForm',
	'PrizeTicketFormSet',
  'DonorSearchForm',
  'RunSearchForm',
  'BidSearchForm',
  'PrizeSearchForm',
  'EventFilterForm',
  'PrizeSubmissionForm',
]

class UsernameForm(forms.Form):
  username = forms.CharField(
    max_length=255,
    widget=forms.TextInput(attrs={'class': 'required username'}))
  def clean_username(self):
    if 'username' in self.cleaned_data:
      username = self.cleaned_data['username']
      if not re.match(r'^[a-zA-Z0-9_]+$', username):
        raise forms.ValidationError(_("Usernames can only contain letters, numbers, and the underscore"))
      if username[:10]=='openiduser':
        raise forms.ValidationError(_("Username may not start with 'openiduser'"))
      if User.objects.filter(username=username).count() > 0:
        raise forms.ValidationError(_("Username already in use"))
      return self.cleaned_data['username']

class DonationCredentialsForm(forms.Form):
  paypalemail = forms.EmailField(min_length=1, label="Paypal Email")
  amount = forms.DecimalField(decimal_places=2, min_value=Decimal('0.00'), label="Donation Amount")
  transactionid = forms.CharField(min_length=1, label="Transaction ID")

class DonationEntryForm(forms.Form):
  amount = forms.DecimalField(decimal_places=2, min_value=Decimal('0.00'), label="Donation Amount", widget=forms.TextInput(attrs={'id':'iDonationAmount', 'type':'text'}), required=True)
  comment = forms.CharField(widget=forms.Textarea, required=False)
  hasbid = forms.BooleanField(initial=False, required=False, label="Is this a bid suggestion?")
  requestedvisibility = forms.ChoiceField(initial='CURR', choices=models.Donation._meta.get_field('requestedvisibility').choices, label='Name Visibility')
  requestedalias = forms.CharField(max_length=32, label='Preferred Alias', required=False)
  requestedemail = forms.EmailField(max_length=128, label='Preferred Email', required=False)
  def clean(self):
    if self.cleaned_data['requestedvisibility'] == 'ALIAS' and not self.cleaned_data['requestedalias']:
      raise forms.ValidationError(_("Must specify an alias with 'ALIAS' visibility"))
    return self.cleaned_data

class DonationBidForm(forms.Form):
  bid = forms.fields.IntegerField(label="", required=False, widget=tracker.widgets.MegaFilterWidget(model="bidtarget"))
  amount = forms.DecimalField(decimal_places=2,max_digits=20, required=False, validators=[positive,nonzero], widget=forms.widgets.TextInput(attrs={'class': 'cdonationbidamount', 'type':'number'}))
  def clean_bid(self):
    try:
      bid = self.cleaned_data['bid']
      if not bid:
        bid = None
      else:
        bid = models.Bid.objects.get(id=bid)
        if bid.state == 'CLOSED':
          raise forms.ValidationError("This bid not open for new donations anymore.")
    except Exception as e:
      raise forms.ValidationError("Bid does not exist.")
    return bid
  def clean(self):
    if self.cleaned_data['amount'] and (not ('bid' in self.cleaned_data) or not self.cleaned_data['bid']):
      raise forms.ValidationError(_("Error, did not specify a bid"))
    if self.cleaned_data['bid'] and not self.cleaned_data['amount']:
      raise forms.ValidationError(_("Error, did not specify an amount"))
    return self.cleaned_data
      
class DonationBidFormSetBase(forms.formsets.BaseFormSet):
  max_bids = 10
  def __init__(self, amount=Decimal('0.00'), *args, **kwargs):
    self.amount = amount
    super(DonationBidFormSetBase, self).__init__(*args, **kwargs)
  def clean(self):
    if any(self.errors):
      # Don't bother validating the formset unless each form is valid on its own
      return
    if len(self.forms) > DonationBidFormSetBase.max_bids:
      self.forms[0].errors['__all__'] = self.error_class(["Error, cannot submit more than " + str(DonationBidFormSetBase.max_bids) + " bids."])
      raise forms.ValidationError("Error, cannot submit more than " + str(DonationBidFormSetBase.max_bids) + " bids.")
    sumAmount = Decimal('0.00')
    for form in self.forms:
      if form.cleaned_data.get('amount', None):
        sumAmount += form.cleaned_data['amount']
      if sumAmount > self.amount:
        form.errors['__all__'] = form.error_class(["Error, total bid amount cannot exceed donation amount."])
        raise forms.ValidationError("Error, total bid amount cannot exceed donation amount.")
  
DonationBidFormSet = formsets.formset_factory(DonationBidForm, formset=DonationBidFormSetBase, max_num=DonationBidFormSetBase.max_bids)

class PrizeTicketForm(forms.Form):
  prize = forms.fields.IntegerField(label="", required=False, widget=tracker.widgets.MegaFilterWidget(model="prize"))
  amount = forms.DecimalField(decimal_places=2,max_digits=20, required=False, validators=[positive,nonzero], widget=forms.widgets.TextInput(attrs={'class': 'cprizeamount', 'type':'number'}))
  def clean_prize(self):
    try:
      prize = self.cleaned_data['prize']
      if not prize:
        prize = None
      else:
        prize = models.Prize.objects.get(id=prize)
        if prize.maxed_winners():
          raise forms.ValidationError("This prize has already been drawn.")
    except Exception as e:
      raise forms.ValidationError("Prize does not exist.")
    return prize
  def clean(self):
    if self.cleaned_data['amount'] and (not ('prize' in self.cleaned_data) or not self.cleaned_data['prize']):
      raise forms.ValidationError(_("Error, did not specify a prize"))
    if self.cleaned_data['prize'] and not self.cleaned_data['amount']:
      raise forms.ValidationError(_("Error, did not specify an amount"))
    return self.cleaned_data
      
class PrizeTicketFormSetBase(forms.formsets.BaseFormSet):
  max_tickets = 10
  def __init__(self, amount=Decimal('0.00'), *args, **kwargs):
    self.amount = amount
    super(PrizeTicketFormSetBase, self).__init__(*args, **kwargs)
  def clean(self):
    if any(self.errors):
      # Don't bother validating the formset unless each form is valid on its own
      return
    if len(self.forms) > PrizeTicketFormSetBase.max_tickets:
      self.forms[0].errors['__all__'] = self.error_class(["Error, cannot submit more than " + str(PrizeTicketFormSetBase.max_tickets) + " prize tickets per donation."])
      raise forms.ValidationError("Error, cannot submit more than " + str(PrizeTicketFormSetBase.max_tickets) + " prize tickets.")
    sumAmount = Decimal('0.00')
    for form in self.forms:
      if form.cleaned_data.get('amount', None):
        sumAmount += form.cleaned_data['amount']
      if sumAmount > self.amount:
        form.errors['__all__'] = form.error_class(["Error, total ticket amount cannot exceed donation amount."])
        raise forms.ValidationError("Error, total ticket amount cannot exceed donation amount.")
  
PrizeTicketFormSet = formsets.formset_factory(PrizeTicketForm, formset=PrizeTicketFormSetBase, max_num=PrizeTicketFormSetBase.max_tickets)

class DonorSearchForm(forms.Form):
  q = forms.CharField(required=False, initial=None, max_length=255, label='Search')

class DonationSearchForm(forms.Form):
  feed = forms.ChoiceField(required=False, initial='recent', choices=(('all', 'All'), ('recent', 'Recent')), label='Filter')
  q = forms.CharField(required=False, initial=None, max_length=255, label='Search')
  
class BidSearchForm(forms.Form):
  feed = forms.ChoiceField(required=False, initial='current', choices=(('all', 'All'), ('current', 'Current'), ('future', 'Future'), ('open','Open'), ('closed', 'Closed')), label='Type')
  q = forms.CharField(required=False, initial=None, max_length=255, label='Search')

class RunSearchForm(forms.Form):
  feed = forms.ChoiceField(required=False, initial='current', choices=(('all','All'), ('current','Current'), ('future', 'Future')), label='Type')
  q = forms.CharField(required=False, initial=None, max_length=255, label='Search')

class PrizeSearchForm(forms.Form):
  feed = forms.ChoiceField(required=False, initial='upcomming', choices=(('all', 'All'), ('unwon', 'Not Drawn'), ('won', 'Drawn'), ('current', 'Current'), ('future', 'Future')), label='Type')
  q = forms.CharField(required=False, initial=None, max_length=255, label='Search')

class RootDonorForm(forms.Form):
  def __init__(self, donors, *args, **kwargs):
    super(RootDonorForm, self).__init__(*args, **kwargs)
    choices = []
    for donor in donors:
      choices.append((donor, unicode(models.Donor.objects.get(id=donor))))
    self.fields['rootdonor'] = forms.ChoiceField(choices=choices, required=True)
    self.fields['donors'] = forms.CharField(initial=','.join([str(i) for i in donors]), widget=forms.HiddenInput())

class EventFilterForm(forms.Form):
  def __init__(self, * args, **kwargs):
    super(EventFilterForm, self).__init__(*args, **kwargs)
    self.fields['event'] = forms.ModelChoiceField(queryset=models.Event.objects.all(), empty_label="All Events", required=False)
    
class PrizeSubmissionForm(forms.Form):
  name = forms.CharField(max_length=64, required=True, label="Prize Name",
    help_text="Please use a name that will uniquely identify your prize throughout the event.");
  description = forms.CharField(max_length=1024, required=True, label="Prize Description", widget=forms.Textarea,
    help_text="Briefly describe your prize, as you would like it to appear to the public. All descriptions are subject to editing at our discretion.")
  maxwinners = forms.IntegerField(required=True, initial=1, widget=tracker.widgets.NumberInput({'min': 1, 'max': 10}), label="Number of Copies",
    help_text="If you are submitting multiple copies of the same prize (e.g. multiple copies of the same print), specify how many. Otherwise, leave this at 1.")
  extrainfo = forms.CharField(max_length=1024, required=False, label="Extra/Non-Public Information", widget=forms.Textarea,
    help_text="Enter any additional information you feel the staff should know about your prize. This information will not be made public. Examples include suggesting games for the prize.")
  estimatedvalue = forms.DecimalField(decimal_places=2,max_digits=20, required=False, label='Estimated Value',validators=[positive,nonzero],
    help_text="Estimate the actual value of the prize in US Dollars. If the prize is handmade, use your best judgement based on time spent creating it. Note that this is not the bid amount. Leave blank if you prefer this information not be made public." )
  suggestedamount = forms.DecimalField(decimal_places=2,max_digits=20, required=False, label='Suggested Minimum Donation',validators=[positive,nonzero],
    help_text="Specify the donation amount (in USD) you believe should enter a donor to win this prize. This amount may be modified by GamesDoneQuick staff at their discretion." )
  imageurl = forms.URLField(max_length=1024, label='Prize Image', required=True, 
    help_text="Enter the URL of an image of the prize. Please see our additional notes regarding prize images. Images are now required for prize submissions.")
  creatorname = forms.CharField(max_length=64, required=False, label="Prize Creator",
    help_text="Name of the creator of the prize. This is for crediting/promoting the artists who created this content.")
  creatoremail = forms.EmailField(max_length=128, label='Prize Creator Email', required=False, 
    help_text="Enter an e-mail if the creator of this prize accepts comissions and would like to be promoted through our marathon. Do not enter an e-mail unless they are known to accept comissions, or you have received their explicit consent.")
  creatorwebsite = forms.URLField(max_length=1024, label='Prize Creator Website', required=False, 
    help_text="Enter the URL of the prize creator's website or online storefront if applicable.")
  providername = forms.CharField(max_length=64, required=False, label="Your Name",
    help_text="How would you like to be credited with the contribution of this prize (e.g. SDA forum name, or real name)? Leave blank if you would like to remain anonymous to the public.");
  provideremail = forms.EmailField(max_length=128, label='Your Contact Email', required=True, 
    help_text="This address will be used to contact you, for example to confirm if your prize will be included in the event, and with shipping details (if neccessary) after the event. This e-mail is required, but will never be given to the public." )
  agreement = forms.BooleanField(label="Agreement", help_text="Check if you agree to the following: I am expected to ship the prize myself, and will keep a receipt to be reimbursed for the cost of shipping. I currently have the prize in my possesion, or can guarantee that I can obtain it within one week of the start of the marathon. I agree to communicate with the staff in a timely manner as neccessary regarding this prize. I agree that all contact information is correct has been provided with the consent of the respective parties. I agree that if the prize is no longer available, I will contact the staff immediately to withdraw it, and no later than one week within the start date of the marathon.")
  def clean_name(self):
    basename = self.cleaned_data['name']
    prizes = models.Prize.objects.filter(name=basename)
    if not prizes.exists():
      return basename
    name = basename
    count = 1
    while prizes.exists():
      count += 1
      name = basename + ' ' + str(count)
      prizes = models.Prize.objects.filter(name=name)
    raise forms.ValidationError('Prize name taken. Suggestion: "{0}"'.format(name))
  def clean_agreement(self):
    value = self.cleaned_data['agreement']
    if not value:
      raise forms.ValidationError("You must agree with this statement to submit a prize.")
    return value
  def clean_suggestedamount(self):
    amount = self.cleaned_data['suggestedamount']
    if not amount:
      amount = Decimal('5.00')
    return amount