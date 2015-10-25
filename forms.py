from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.template import Template
from tracker import models

import post_office
import post_office.models

import tracker.viewutil as viewutil
import tracker.auth as auth
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
  'MergeObjectsForm',
  'EventFilterForm',
  'PrizeSubmissionForm',
  'AutomailPrizeContributorsForm',
  'DrawPrizeWinnersForm',
  'AutomailPrizeWinnersForm',
  'PostOfficePasswordResetForm',
  'RegistrationConfirmationForm',
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
  amount = forms.DecimalField(decimal_places=2, min_value=Decimal('0.01'), label="Donation Amount", widget=tracker.widgets.NumberInput(attrs={'id':'iDonationAmount', 'step':'0.01'}), required=True)
  comment = forms.CharField(widget=forms.Textarea, required=False)
  requestedvisibility = forms.ChoiceField(initial='CURR', choices=models.Donation._meta.get_field('requestedvisibility').choices, label='Name Visibility')
  requestedalias = forms.CharField(max_length=32, label='Preferred Alias', required=False)
  requestedemail = forms.EmailField(max_length=128, label='Preferred Email', required=False)
  def clean_amount(self):
    amount = self.cleaned_data.get('amount')
    if not amount or amount <= Decimal('0.00'):
      raise forms.ValidationError(_('Donation amount must be greater than zero.'))
    return self.cleaned_data['amount']
  def clean(self):
    if self.cleaned_data['requestedvisibility'] == 'ALIAS' and not self.cleaned_data['requestedalias']:
      raise forms.ValidationError(_("Must specify an alias with 'ALIAS' visibility"))
    if self.cleaned_data['requestedalias'] and self.cleaned_data['requestedalias'].lower() == 'anonymous':
      self.cleaned_data['requestedalias'] = ''
      self.cleaned_data['requestedvisibility'] = 'ANON'
    return self.cleaned_data

class DonationBidForm(forms.Form):
  bid = forms.fields.IntegerField(label="", required=False, widget=tracker.widgets.MegaFilterWidget(model="bidtarget"))
  customoptionname = forms.fields.CharField(max_length=models.Bid._meta.get_field('name').max_length, label='New Option Name:', required=False)
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
  def clean_amount(self):
    try:
      amount = self.cleaned_data['amount']
      if not amount:
        amount = None
      else:
        amount = Decimal(amount)
    except Exception as e:
      raise forms.ValidationError('Could not parse amount.')
    return amount
  def clean_customoptionname(self):
    return self.cleaned_data['customoptionname'].strip()
  def clean(self):
    if 'amount' not in self.cleaned_data:
      self.cleaned_data['amount'] = None
    if 'bid' not in self.cleaned_data:
      self.cleaned_data['bid'] = None
    if self.cleaned_data['amount'] and not self.cleaned_data['bid']:
      raise forms.ValidationError(_("Error, did not specify a bid"))
    if self.cleaned_data['bid'] and not self.cleaned_data['amount']:
      raise forms.ValidationError(_("Error, did not specify an amount"))
    if self.cleaned_data['bid']:
      if self.cleaned_data['bid'].allowuseroptions:
        if not self.cleaned_data['customoptionname']:
          raise forms.ValidationError(_('Error, did not specify a name for the custom option.'))
        elif self.cleaned_data['amount'] < Decimal('1.00'):
          raise forms.ValidationError(_('Error, you must bid at least one dollar for a custom bid.'))
      else:
        if self.cleaned_data['customoptionname']:
          raise forms.ValidationError(_('Error, specified custom data for a non-custom bid'))
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
    bids = set()
    for form in self.forms:
      if 'bid' in form.cleaned_data:
        if form.cleaned_data.get('amount', None):
          sumAmount += form.cleaned_data['amount']
        if sumAmount > self.amount:
          form.errors['__all__'] = form.error_class(["Error, total bid amount cannot exceed donation amount."])
          raise forms.ValidationError("Error, total bid amount cannot exceed donation amount.")
        if form.cleaned_data['bid'] in bids:
          form.errors['__all__'] = form.error_class(["Error, cannot bid more than once for the same bid in the same donation."])
          raise forms.ValidationError("Error, cannot bid more than once for the same bid in the same donation.")
        bids.add(form.cleaned_data['bid'])
  
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
    currentPrizes = set()
    for form in self.forms:
      if 'prize' in form.cleaned_data:
        if form.cleaned_data['prize'] in currentPrizes:
          form.errors['__all__'] = form.error_class(["Error, cannot bid more than once for the same bid in the same donation."])
          raise forms.ValidationError("Error, cannot bid more than once for the same bid in the same donation.")
        if form.cleaned_data.get('amount', None):
          sumAmount += form.cleaned_data['amount']
        if sumAmount > self.amount:
          form.errors['__all__'] = form.error_class(["Error, total ticket amount cannot exceed donation amount."])
          raise forms.ValidationError("Error, total ticket amount cannot exceed donation amount.")
        currentPrizes.add(form.cleaned_data['prize'])
  
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

class MergeObjectsForm(forms.Form):
  def __init__(self, model, objects, *args, **kwargs):
    super(MergeObjectsForm, self).__init__(*args, **kwargs)
    self.model = model
    self.choices = []
    for objId in objects:
      self.choices.append((objId, unicode(self.model.objects.get(id=objId))))
    self.fields['root'] = forms.ChoiceField(choices=self.choices, required=True)
    self.fields['objects'] = forms.CharField(initial=','.join([str(i) for i in objects]), widget=forms.HiddenInput())
  def clean(self):
    root = self.model.objects.get(id=self.cleaned_data['root'])
    objects = []
    for objId in map(lambda x: int(x), filter(lambda x: bool(x), self.cleaned_data['objects'].split(','))):
      if objId != root.id:
        objects.append(self.model.objects.get(id=objId))
    self.cleaned_data['root'] = root
    self.cleaned_data['objects'] = objects
    return self.cleaned_data

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
    self.fields['prizes'] = forms.TypedMultipleChoiceField(choices=self.choices, initial=[prize.id for prize in prizes], label='Prizes', empty_value='', widget=forms.widgets.CheckboxSelectMultiple)
  def clean(self):
    if not self.cleaned_data['replyaddress']:
      self.cleaned_data['replyaddress'] = self.cleaned_data['fromaddress']
    self.cleaned_data['prizes'] = list(map(lambda x: models.Prize.objects.get(id=x), self.cleaned_data['prizes']))
    return self.cleaned_data
    
class DrawPrizeWinnersForm(forms.Form):
  def __init__(self, prizes, *args, **kwargs):
    super(DrawPrizeWinnersForm, self).__init__(*args, **kwargs)
    self.choices = []
    for prize in prizes:
      self.choices.append((prize.id, mark_safe(format_html(u'<a href="{0}">{1}</a>', viewutil.admin_url(prize), prize))))
    self.fields['prizes'] = forms.TypedMultipleChoiceField(choices=self.choices, initial=[prize.id for prize in prizes], coerce=lambda x: int(x), label='Prizes', empty_value='', widget=forms.widgets.CheckboxSelectMultiple)
    self.fields['seed'] = forms.IntegerField(required=False, label='Random Seed', help_text="Completely optional, if you don't know what this is, don't worry about it")
  def clean(self):
    self.cleaned_data['prizes'] = list(map(lambda x: models.Prize.objects.get(id=x), self.cleaned_data['prizes']))
    return self.cleaned_data
    
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
    self.fields['prizewinners'] = forms.TypedMultipleChoiceField(choices=self.choices, initial=[prizewinner.id for prizewinner in prizewinners], coerce=lambda x: int(x), label='Prize Winners', empty_value='', widget=forms.widgets.CheckboxSelectMultiple)
  def clean(self):
    if not self.cleaned_data['replyaddress']:
      self.cleaned_data['replyaddress'] = self.cleaned_data['fromaddress']
    self.cleaned_data['prizewinners'] = list(map(lambda x: models.PrizeWinner.objects.get(id=x), self.cleaned_data['prizewinners']))
    return self.cleaned_data

class PostOfficePasswordResetForm(forms.Form):
    email = forms.EmailField(label=u'Email', max_length=254)

    def get_user(self):
        AuthUser = get_user_model()
        email = self.cleaned_data['email']
        userSet = AuthUser.objects.filter(email__iexact=email, is_active=True)
        if not userSet.exists():
            raise forms.ValidationError('User with email {0} does not exist.'.format(email))
        elif userSet.count() != 1:
            raise forms.ValidationError('More than one user has the e-mail {0}. Ideally this would be a db constraint, but django is stupid.'.format(email))
        return userSet[0]

    def clean_email(self):
        return self.get_user().email

    def save(self, email_template_name=None, use_https=False, token_generator=default_token_generator, from_email=None, request=None, email_template=None, **kwargs):
        if not email_template:
            email_template = email_template_name
        if not email_template:
            email_template = auth.get_password_reset_email_template()
        user = self.get_user()
        domain = viewutil.get_request_server_url(request)
        return auth.send_password_reset_mail(domain, user, email_template, sender=from_email, token_generator=token_generator)

class RegistrationForm(forms.Form):
    email = forms.EmailField(label=u'Email', max_length=254, required=True)

    def clean_email(self):
        user = self.get_existing_user()
        if user is not None and user.is_active:
            raise forms.ValidationError('This email is already registered. Please log in, (or reset your password if you forgot it).')
        return self.cleaned_data['email']

    def save(self, email_template=None, use_https=False, token_generator=default_token_generator, from_email=None, request=None, **kwargs):
        if not email_template:
            email_template = auth.get_register_email_template()
        user = self.get_existing_user()
        email = self.cleaned_data['email']
        if user is None:
            AuthUser = get_user_model()
            user = AuthUser.objects.create(username=email,email=email,is_active=False)
        domain = viewutil.get_request_server_url(request)
        return auth.send_registration_mail(domain, user, template=email_template, sender=from_email, token_generator=token_generator)

    def get_existing_user(self):
        AuthUser = get_user_model()
        email = self.cleaned_data['email']
        userSet = AuthUser.objects.filter(email__iexact=email)
        if userSet.count() > 1:
            raise forms.ValidationError('More than one user has the e-mail {0}. Ideally this would be a db constraint, but django is stupid. Contact SMK to get this sorted out.'.format(email))
        if userSet.exists():
            return userSet[0]
        else:
            return None

class RegistrationConfirmationForm(forms.Form):
  username = forms.CharField(label=u'User Name', max_length=30, required=True)
  password = forms.CharField(label=u'Password', widget=forms.PasswordInput(), required=True)
  passwordconfirm = forms.CharField(label=u'Confirm Password', widget=forms.PasswordInput(), required=True)
  def __init__(self, user, token, token_generator=default_token_generator, *args, **kwargs):
    super(RegistrationConfirmationForm,self).__init__(*args,**kwargs)    
    self.user = user
    self.token = token
    self.token_generator = token_generator
    if not self.check_token():
      self.fields = {}
  def check_token(self):
    if self.user and not self.user.is_active and self.token and self.token_generator:
      return self.token_generator.check_token(self.user, self.token)
    else:
      return False
  def clean_username(self):
    AuthUser = get_user_model()
    usersWithName = AuthUser.objects.filter(username__iexact=self.cleaned_data['username'])
    if not usersWithName.exists() or (usersWithName.count() == 1 and usersWithName[0] == self.user):
      return self.cleaned_data['username']
    raise forms.ValidationError('Username {0} is already taken'.format(self.cleaned_data['username'])) 
  def clean_password(self):
    if not self.cleaned_data['password']:
      raise forms.ValidationError('Password must not be blank.')
    return self.cleaned_data['password']
  def clean(self):
    if not self.check_token():
      raise forms.ValidationError('User token pair is not valid.')
    if self.cleaned_data['password'] != self.cleaned_data['passwordconfirm']:
      raise forms.ValidationError('Passwords must match.')
    return self.cleaned_data
  def save(self):
    if self.user:
      self.user.username = self.cleaned_data['username']
      self.user.set_password(self.cleaned_data['password'])
      self.user.is_active = True
      self.user.save()
    else:
      raise forms.ValidationError('Could not save user.')

