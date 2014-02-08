from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from tracker import models
import paypal
import re
from decimal import *
from django.forms import formsets;
import django.core.exceptions;

import tracker.fields;
import tracker.widgets;

def positive(value):
  if value <  0: raise ValidationError('Value cannot be negative')

def nonzero(value):
  if value == 0: raise ValidationError('Value cannot be zero') 

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
  paypalemail = forms.EmailField(min_length=1, label="Paypal Email");
  amount = forms.DecimalField(decimal_places=2, min_value=Decimal('0.00'), label="Donation Amount");
  transactionid = forms.CharField(min_length=1, label="Transaction ID");

class DonationEntryForm(forms.Form):
  amount = forms.DecimalField(decimal_places=2, min_value=Decimal('0.00'), label="Donation Amount", widget=forms.TextInput(attrs={'id':'iDonationAmount', 'type':'text'}), required=True);
  comment = forms.CharField(widget=forms.Textarea, required=False);
  hasbid = forms.BooleanField(initial=False, required=False, label="Is this a bid suggestion?");
  requestedvisibility = forms.ChoiceField(initial='CURR', choices=models.Donation._meta.get_field('requestedvisibility').choices, label='Name Visibility');
  requestedalias = forms.CharField(max_length=32, label='Preferred Alias', required=False);
  requestedemail = forms.EmailField(max_length=128, label='Preferred Email', required=False);
  def clean(self):
    if self.cleaned_data['requestedvisibility'] == 'ALIAS' and not self.cleaned_data['requestedalias']:
      raise forms.ValidationError(_("Must specify an alias with 'ALIAS' visibility"));
    return self.cleaned_data;

class DonationBidForm(forms.Form):
  bid = forms.fields.IntegerField(label="", required=False, widget=tracker.widgets.MegaFilterWidget(model="bidtarget"));
  amount = forms.DecimalField(decimal_places=2,max_digits=20, required=False, validators=[positive,nonzero], widget=forms.widgets.TextInput(attrs={'class': 'cdonationbidamount', 'type':'number'}));
  def clean_bid(self):
    try:
      bid = self.cleaned_data['bid'];
      if not bid:
        bid = None;
      else:
        bid = models.Bid.objects.get(id=bid);
        if bid.state == 'CLOSED':
          raise forms.ValidationError("This bid not open for new donations anymore.");
    except Exception as e:
      raise forms.ValidationError("Bid does not exist.");
    return bid;
  def clean(self):
    if self.cleaned_data['amount'] and (not ('bid' in self.cleaned_data) or not self.cleaned_data['bid']):
      raise forms.ValidationError(_("Error, did not specify a bid"));
    if self.cleaned_data['bid'] and not self.cleaned_data['amount']:
      raise forms.ValidationError(_("Error, did not specify an amount"));
    return self.cleaned_data;
      
class DonationBidFormSetBase(forms.formsets.BaseFormSet):
  max_bids = 10;
  def __init__(self, amount=Decimal('0.00'), *args, **kwargs):
    self.amount = amount;
    super(DonationBidFormSetBase, self).__init__(*args, **kwargs);
  def clean(self):
    if any(self.errors):
      # Don't bother validating the formset unless each form is valid on its own
      return;
    if len(self.forms) > DonationBidFormSetBase.max_bids:
      self.forms[0].errors['__all__'] = self.error_class(["Error, cannot submit more than " + str(DonationBidFormSetBase.max_bids) + " bids."]);
      raise forms.ValidationError("Error, cannot submit more than " + str(DonationBidFormSetBase.max_bids) + " bids.");
    sumAmount = Decimal('0.00');
    for form in self.forms:
      if form.cleaned_data.get('amount', None):
        sumAmount += form.cleaned_data['amount'];
      if sumAmount > self.amount:
        form.errors['__all__'] = form.error_class(["Error, total bid amount cannot exceed donation amount."]);
        raise forms.ValidationError("Error, total bid amount cannot exceed donation amount.");
  
DonationBidFormSet = formsets.formset_factory(DonationBidForm, formset=DonationBidFormSetBase, max_num=DonationBidFormSetBase.max_bids);

class PrizeTicketForm(forms.Form):
  prize = forms.fields.IntegerField(label="", required=False, widget=tracker.widgets.MegaFilterWidget(model="prize"));
  amount = forms.DecimalField(decimal_places=2,max_digits=20, required=False, validators=[positive,nonzero], widget=forms.widgets.TextInput(attrs={'class': 'cprizeamount', 'type':'number'}));
  def clean_prize(self):
    try:
      prize = self.cleaned_data['prize'];
      if not prize:
        prize = None;
      else:
        prize = models.Prize.objects.get(id=prize);
        if prize.maxed_winners():
          raise forms.ValidationError("This prize has already been drawn.");
    except Exception as e:
      raise forms.ValidationError("Prize does not exist.");
    return prize;
  def clean(self):
    if self.cleaned_data['amount'] and (not ('prize' in self.cleaned_data) or not self.cleaned_data['prize']):
      raise forms.ValidationError(_("Error, did not specify a prize"));
    if self.cleaned_data['prize'] and not self.cleaned_data['amount']:
      raise forms.ValidationError(_("Error, did not specify an amount"));
    return self.cleaned_data;
      
class PrizeTicketFormSetBase(forms.formsets.BaseFormSet):
  max_tickets = 10;
  def __init__(self, amount=Decimal('0.00'), *args, **kwargs):
    self.amount = amount;
    super(PrizeTicketFormSetBase, self).__init__(*args, **kwargs);
  def clean(self):
    if any(self.errors):
      # Don't bother validating the formset unless each form is valid on its own
      return;
    if len(self.forms) > PrizeTicketFormSetBase.max_tickets:
      self.forms[0].errors['__all__'] = self.error_class(["Error, cannot submit more than " + str(PrizeTicketFormSetBase.max_tickets) + " prize tickets per donation."]);
      raise forms.ValidationError("Error, cannot submit more than " + str(PrizeTicketFormSetBase.max_tickets) + " prize tickets.");
    sumAmount = Decimal('0.00');
    for form in self.forms:
      if form.cleaned_data.get('amount', None):
        sumAmount += form.cleaned_data['amount'];
      if sumAmount > self.amount:
        form.errors['__all__'] = form.error_class(["Error, total ticket amount cannot exceed donation amount."]);
        raise forms.ValidationError("Error, total ticket amount cannot exceed donation amount.");
  
PrizeTicketFormSet = formsets.formset_factory(PrizeTicketForm, formset=PrizeTicketFormSetBase, max_num=PrizeTicketFormSetBase.max_tickets);

class DonorSearchForm(forms.Form):
  q = forms.CharField(required=False, initial=None, max_length=255, label='Search');

class DonationSearchForm(forms.Form):
  feed = forms.ChoiceField(required=False, initial='recent', choices=(('all', 'All'), ('recent', 'Recent')), label='Filter')
  q = forms.CharField(required=False, initial=None, max_length=255, label='Search');
  
class BidSearchForm(forms.Form):
  feed = forms.ChoiceField(required=False, initial='current', choices=(('all', 'All'), ('current', 'Current'), ('future', 'Future'), ('open','Open'), ('closed', 'Closed')), label='Type');
  q = forms.CharField(required=False, initial=None, max_length=255, label='Search');

class RunSearchForm(forms.Form):
  feed = forms.ChoiceField(required=False, initial='current', choices=(('all','All'), ('current','Current'), ('future', 'Future')), label='Type')
  q = forms.CharField(required=False, initial=None, max_length=255, label='Search');

class PrizeSearchForm(forms.Form):
  feed = forms.ChoiceField(required=False, initial='upcomming', choices=(('all', 'All'), ('unwon', 'Not Drawn'), ('won', 'Drawn'), ('current', 'Current'), ('future', 'Future')), label='Type')
  q = forms.CharField(required=False, initial=None, max_length=255, label='Search');

class RootDonorForm(forms.Form):
  def __init__(self, donors, *args, **kwargs):
    super(RootDonorForm, self).__init__(*args, **kwargs)
    choices = [];
    for donor in donors:
      choices.append((donor, unicode(models.Donor.objects.get(id=donor))));
    self.fields['rootdonor'] = forms.ChoiceField(choices=choices, required=True);
    self.fields['donors'] = forms.CharField(initial=','.join([str(i) for i in donors]), widget=forms.HiddenInput());

class EventFilterForm(forms.Form):
  def __init__(self, * args, **kwargs):
    super(EventFilterForm, self).__init__(*args, **kwargs);
    self.fields['event'] = forms.ModelChoiceField(queryset=models.Event.objects.all(), empty_label="All Events", required=False);
