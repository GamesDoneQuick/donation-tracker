from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from tracker import models
import paypal
import re
from decimal import *

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

class DonationPostbackForm(forms.Form):
  comment = forms.CharField(widget=forms.Textarea);

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
  feed = forms.ChoiceField(required=False, initial='upcomming', choices=(('all', 'All'), ('unwon', 'Not Drawn'), ('won', 'Drawn'), ('current', 'Current'), ('upcomming', 'Upcomming')), label='Type')
  q = forms.CharField(required=False, initial=None, max_length=255, label='Search');

