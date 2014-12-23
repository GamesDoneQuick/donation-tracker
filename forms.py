from django import forms
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.template import Template
from tracker import models

import post_office

import tracker.viewutil as viewutil
from tracker.validators import *
import paypal
import re
from decimal import *
from django.forms import formsets
import django.core.exceptions
import settings

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
  amount = forms.DecimalField(decimal_places=2, min_value=Decimal('0.00'), label="Donation Amount", widget=tracker.widgets.NumberInput(attrs={'id':'iDonationAmount', 'step':'0.01'}), required=True)
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
  amount = forms.DecimalField(decimal_places=2,max_digits=20, required=False, validators=[positive,nonzero], widget=tracker.widgets.NumberInput(attrs={'class': 'cdonationbidamount', 'step':'0.01'}))
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
  amount = forms.DecimalField(decimal_places=2,max_digits=20, required=False, validators=[positive,nonzero], widget=tracker.widgets.NumberInput(attrs={'class': 'cprizeamount', 'step':'0.01'}))
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
    self.choices = []
    for donor in donors:
      self.choices.append((donor, unicode(models.Donor.objects.get(id=donor))))
    self.fields['rootdonor'] = forms.ChoiceField(choices=self.choices, required=True)
    self.fields['donors'] = forms.CharField(initial=','.join([str(i) for i in donors]), widget=forms.HiddenInput())

class EventFilterForm(forms.Form):
  def __init__(self, * args, **kwargs):
    super(EventFilterForm, self).__init__(*args, **kwargs)
    self.fields['event'] = forms.ModelChoiceField(queryset=models.Event.objects.all(), empty_label="All Events", required=False)
    
class PrizeSubmissionForm(forms.Form):
  name = forms.CharField(max_length=64, required=True, label="Prize Name",
    help_text="Please use a name that will uniquely identify your prize throughout the event.")
  description = forms.CharField(max_length=1024, required=True, label="Prize Description", widget=forms.Textarea,
    help_text="Briefly describe your prize, as you would like it to appear to the public. All descriptions are subject to editing at our discretion.")
  maxwinners = forms.IntegerField(required=True, initial=1, widget=tracker.widgets.NumberInput({'min': 1, 'max': 10}), label="Number of Copies",
    help_text="If you are submitting multiple copies of the same prize (e.g. multiple copies of the same print), specify how many. Otherwise, leave this at 1.")
  startrun = forms.fields.IntegerField(label="Suggested Start Game", required=False, widget=tracker.widgets.MegaFilterWidget(model="run"), 
    help_text="If you feel your prize would fit with a specific game (or group of games), enter them here. Please specify the games in the order that they will appear in the marathon.")
  endrun = forms.fields.IntegerField(label="Suggested End Game", required=False, widget=tracker.widgets.MegaFilterWidget(model="run"),
    help_text="Leaving only one or the other field blank will simply set the prize to only cover the one game")
  extrainfo = forms.CharField(max_length=1024, required=False, label="Extra/Non-Public Information", widget=forms.Textarea,
    help_text="Enter any additional information you feel the staff should know about your prize. This information will not be made public. ")
  estimatedvalue = forms.DecimalField(decimal_places=2,max_digits=20, required=False, label='Estimated Value',validators=[positive,nonzero],
    help_text="Estimate the actual value of the prize. If the prize is handmade, use your best judgement based on time spent creating it. Note that this is not the bid amount. Leave blank if you prefer this information not be made public." )
  suggestedamount = forms.DecimalField(decimal_places=2,max_digits=20, required=False, label='Suggested Minimum Donation',validators=[positive,nonzero],
    help_text="Specify the donation amount (in USD) you believe should enter a donor to win this prize. This amount may be modified by GamesDoneQuick staff at their discretion." )
  imageurl = forms.URLField(max_length=1024, label='Prize Image', required=True, 
    help_text=mark_safe("Enter the URL of an image of the prize. Please see our <a href='imagetips'>additional notes</a> regarding prize images. Images are now required for prize submissions."))
  creatorname = forms.CharField(max_length=64, required=False, label="Prize Creator",
    help_text="Name of the creator of the prize. This is for crediting/promoting the people who created this prize (please fill this in even if you are the creator).")
  creatoremail = forms.EmailField(max_length=128, label='Prize Creator Email', required=False, 
    help_text="Enter an e-mail if the creator of this prize accepts comissions and would like to be promoted through our marathon. Do not enter an e-mail unless they are known to accept comissions, or you have received their explicit consent.")
  creatorwebsite = forms.URLField(max_length=1024, label='Prize Creator Website', required=False, 
    help_text="Enter the URL of the prize creator's website or online storefront if applicable.")
  providername = forms.CharField(max_length=64, required=False, label="Your Name",
    help_text="How would you like to be credited with the contribution of this prize (e.g. SDA forum name, or real name)? Leave blank if you would like to remain anonymous to the public.")
  provideremail = forms.EmailField(max_length=128, label='Your Contact Email', required=True, 
    help_text="This address will be used to contact you, for example to confirm if your prize will be included in the event, and with shipping details (if neccessary) after the event. This e-mail is required, but will never be given to the public." )
  agreement = forms.BooleanField(label="Agreement", help_text=mark_safe("""Check if you agree to the following: 
  <ul>
    <li>I am expected to ship the prize myself, and will keep a receipt to be reimbursed for the cost of shipping.</li>
    <li>I currently have the prize in my possesion, or can guarantee that I can obtain it within one week of the start of the marathon.</li>
    <li>I agree to communicate with the staff in a timely manner as neccessary regarding this prize.</li>
    <li>I agree that all contact information is correct has been provided with the consent of the respective parties.</li>
    <li>I agree that if the prize is no longer available, I will contact the staff immediately to withdraw it, and no later than one month of the start date of the marathon.</li>
  </ul>"""))
  def impl_clean_run(self, data):
    if not data:
      return None
    try:
      result = models.SpeedRun.objects.get(id=data)
      return result
    except:
      raise forms.ValidationError("Invalid Run id.")
  def clean_startrun(self):
    return self.impl_clean_run(self.cleaned_data['startrun'])
  def clean_endrun(self):
    return self.impl_clean_run(self.cleaned_data['endrun'])
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
  def clean(self):
    if not self.cleaned_data['startrun']:
      self.cleaned_data['startrun'] = self.cleaned_data.get('endrun', None)
    if not self.cleaned_data['endrun']:
      self.cleaned_data['endrun'] = self.cleaned_data.get('startrun', None)
    if self.cleaned_data['startrun'] and self.cleaned_data['startrun'].starttime > self.cleaned_data['endrun'].starttime:
      self.errors['startrun'] = "Start run must be before the end run"
      self.errors['endrun'] = "Start run must be before the end run"
      raise forms.ValidationError("Error, Start run must be before the end run")
      #temp = self.cleaned_data['startrun']
      #self.cleaned_data['startrun'] = self.cleaned_data['endrun']
      #self.cleaned_data['endrun'] = temp
    return self.cleaned_data

class AutomailPrizeContributorsForm(forms.Form):
  def __init__(self, prizes, *args, **kwargs):
    super(AutomailPrizeContributorsForm, self).__init__(*args, **kwargs)
    self.choices = []
    prizes = filter(lambda prize: prize.provideremail, prizes)
    for prize in prizes:
      self.choices.append((prize.id, mark_safe(format_html(u'<a href="{0}">{1}</a> State: {2} (<a href="mailto:{3}">{3}</a>)', viewutil.admin_url(prize), prize, prize.get_state_display(), prize.provideremail))))
    self.fields['fromaddress'] = forms.EmailField(max_length=256, initial=settings.EMAIL_HOST_USER, required=True, label='From Address', help_text='Specify the e-mail you would like to identify as the sender')
    self.fields['replyaddress'] = forms.EmailField(max_length=256, required=False, label='Reply Address', help_text="If left blank this will be the same as the from address")
    self.fields['emailtemplate'] = forms.ModelChoiceField(queryset=post_office.models.EmailTemplate.objects.all(), empty_label="Pick a template...", required=True, label='Email Template', help_text="Select an email template to use.")
    self.fields['prizes'] = forms.TypedMultipleChoiceField(choices=self.choices, initial=[prize.id for prize in prizes], coerce=lambda x: models.Prize.objects.get(id=int(x)), label='Prizes', empty_value='', widget=forms.widgets.CheckboxSelectMultiple)
  def clean(self):
    if not self.cleaned_data['replyaddress']:
      self.cleaned_data['replyaddress'] = self.cleaned_data['fromaddress']
    return self.cleaned_data
    
class DrawPrizeWinnersForm(forms.Form):
  def __init__(self, prizes, *args, **kwargs):
    super(DrawPrizeWinnersForm, self).__init__(*args, **kwargs)
    self.choices = []
    for prize in prizes:
      self.choices.append((prize.id, mark_safe(format_html(u'<a href="{0}">{1}</a>', viewutil.admin_url(prize), prize))))
    self.fields['prizes'] = forms.TypedMultipleChoiceField(choices=self.choices, initial=[prize.id for prize in prizes], coerce=lambda x: models.Prize.objects.get(id=int(x)), label='Prizes', empty_value='', widget=forms.widgets.CheckboxSelectMultiple)
    self.fields['seed'] = forms.IntegerField(required=False, label='Random Seed', help_text="Completely optional, if you don't know what this is, don't worry about it")
    
class AutomailPrizeWinnersForm(forms.Form):
  def __init__(self, prizewinners, *args, **kwargs):
    super(AutomailPrizeWinnersForm, self).__init__(*args, **kwargs)
    self.fields['fromaddress'] = forms.EmailField(max_length=256, initial=settings.EMAIL_HOST_USER, required=True, label='From Address', help_text='Specify the e-mail you would like to identify as the sender')
    self.fields['replyaddress'] = forms.EmailField(max_length=256, required=False, label='Reply Address', help_text="If left blank this will be the same as the from address")
    self.fields['emailtemplate'] = forms.ModelChoiceField(queryset=post_office.models.EmailTemplate.objects.all(), initial=None, empty_label="Pick a template...", required=True, label='Email Template', help_text="Select an email template to use.")
    self.choices = []
    for prizewinner in prizewinners:
      winner = prizewinner.winner
      prize = prizewinner.prize
      self.choices.append((prizewinner.id, 
        mark_safe(format_html(u'<a href="{0}">{1}</a>: <a href="{2}">{3}</a>', 
          viewutil.admin_url(prize), prize, viewutil.admin_url(winner), winner))))
    self.fields['prizewinners'] = forms.TypedMultipleChoiceField(choices=self.choices, initial=[prizewinner.id for prizewinner in prizewinners], coerce=lambda x: models.PrizeWinner.objects.get(id=int(x)), label='Prize Winners', empty_value='', widget=forms.widgets.CheckboxSelectMultiple)
  def clean(self):
    if not self.cleaned_data['replyaddress']:
      self.cleaned_data['replyaddress'] = self.cleaned_data['fromaddress']
    return self.cleaned_data
