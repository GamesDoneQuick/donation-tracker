from django.db import models
from django.db.models import Sum,Max
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

import calendar
import urllib2
from datetime import datetime
from decimal import Decimal
import re;
import pytz;

def positive(value):
  if value <  0: raise ValidationError('Value cannot be negative')

def nonzero(value):
  if value == 0: raise ValidationError('Value cannot be zero')

def emptyString(s):
  return s != None and len(s) == 0;
  
_timezoneChoices = list(map(lambda x: (x,x), pytz.common_timezones));
_currencyChoices = (('USD','US Dollars'),('CAD', 'Canadian Dollars'));
  
class Event(models.Model):
  short = models.CharField(max_length=64,unique=True)
  name = models.CharField(max_length=128)
  receivername = models.CharField(max_length=128,blank=True,null=False,verbose_name='Receiver Name')
  targetamount = models.DecimalField(decimal_places=2,max_digits=20,validators=[positive,nonzero],verbose_name='Target Amount')
  usepaypalsandbox = models.BooleanField(default=False,verbose_name='Use Paypal Sandbox');
  paypalemail = models.EmailField(max_length=128,null=False,blank=False, verbose_name='Receiver Paypal')
  paypalcurrency = models.CharField(max_length=8,null=False,blank=False,default=_currencyChoices[0][0],choices=_currencyChoices, verbose_name='Currency')
  scheduleid = models.CharField(max_length=128,unique=True,null=True,blank=True)
  scheduletimezone = models.CharField(max_length=64,blank=True,choices=_timezoneChoices, default='US/Eastern');
  scheduledatetimefield = models.CharField(max_length=128,blank=True)
  schedulegamefield = models.CharField(max_length=128,blank=True)
  schedulerunnersfield = models.CharField(max_length=128,blank=True)
  scheduleestimatefield = models.CharField(max_length=128,blank=True)
  schedulesetupfield = models.CharField(max_length=128,blank=True)
  schedulecommentatorsfield = models.CharField(max_length=128,blank=True)
  schedulecommentsfield = models.CharField(max_length=128,blank=True)
  date = models.DateField()
  def __unicode__(self):
    return self.name
  def clean(self):
    if self.id and self.id < 1:
      raise ValidationError('Event ID must be positive and non-zero')
    if not re.match('^\w+$', self.short):
      raise ValidationError('Event short name must be a url-safe string');
    if emptyString(self.scheduleid):
      self.scheduleid = None;

class Bid(models.Model):
  speedrun = models.ForeignKey('SpeedRun', verbose_name='Run')
  name = models.CharField(max_length=64)
  state = models.CharField(max_length=255,choices=(('HIDDEN', 'Hidden'), ('OPENED','Opened'), ('CLOSED','Closed')))
  description = models.TextField(max_length=1024,null=True,blank=True)
  class Meta:
    abstract = True;
    unique_together = ('speedrun', 'name');
    ordering = ['speedrun__starttime', 'name'];
    permissions = (
      ('view_hidden', 'Can view hidden bids'),
    )
  def __unicode__(self):
    return self.speedrun.name + ' -- ' + self.name;

class Challenge(Bid):
  goal = models.DecimalField(decimal_places=2,max_digits=20)

class ChallengeBid(models.Model):
  challenge = models.ForeignKey('Challenge',related_name='bids')
  donation = models.ForeignKey('Donation')
  amount = models.DecimalField(decimal_places=2,max_digits=20,validators=[positive,nonzero])
  class Meta:
    verbose_name = 'Challenge Bid'
    ordering = [ '-donation__timereceived' ]
  def clean(self):
    self.donation.clean(self)
  def __unicode__(self):
    return unicode(self.challenge) + ' -- ' + unicode(self.donation)

class Choice(Bid):
  pass;

class ChoiceBid(models.Model):
  option = models.ForeignKey('ChoiceOption',related_name='bids')
  donation = models.ForeignKey('Donation')
  amount = models.DecimalField(decimal_places=2,max_digits=20,validators=[positive,nonzero])
  class Meta:
    verbose_name = 'Choice Bid'
    ordering = [ 'option__choice__speedrun__starttime', 'option__choice__name' ]
  def clean(self):
    self.donation.clean(self)
  def __unicode__(self):
    return unicode(self.option) + ' (' + unicode(self.donation.donor) + ') (' + unicode(self.amount) + ')'

class ChoiceOption(models.Model):
  choice = models.ForeignKey('Choice',related_name='option')
  name = models.CharField(max_length=64)
  description = models.CharField(max_length=128,null=True,blank=True)
  class Meta:
    verbose_name = 'Choice Option'
    unique_together = ('choice', 'name')
    ordering = [ 'choice__speedrun__starttime', 'choice__name', 'name']
  def __unicode__(self):
    return unicode(self.choice) + ' -- ' + self.name

class Donation(models.Model):
  donor = models.ForeignKey('Donor')
  event = models.ForeignKey('Event')
  domain = models.CharField(max_length=255,default='LOCAL',choices=(('LOCAL', 'Local'), ('CHIPIN', 'ChipIn'), ('PAYPAL', 'PayPal')))
  domainId = models.CharField(max_length=160,unique=True,editable=False,blank=True)
  transactionstate = models.CharField(max_length=64, default='PENDING', choices=(('PENDING', 'Pending'), ('COMPLETED', 'Completed'), ('CANCELLED', 'Cancelled'), ('FLAGGED', 'Flagged')))
  bidstate = models.CharField(max_length=255,default='PENDING',choices=(('PENDING', 'Pending'), ('IGNORED', 'Ignored'), ('PROCESSED', 'Processed'), ('FLAGGED', 'Flagged')),verbose_name='Bid State')
  readstate = models.CharField(max_length=255,default='PENDING',choices=(('PENDING', 'Pending'), ('IGNORED', 'Ignored'), ('READ', 'Read'), ('FLAGGED', 'Flagged')),verbose_name='Read State')
  commentstate = models.CharField(max_length=255,default='ABSENT',choices=(('ABSENT', 'Absent'), ('PENDING', 'Pending'), ('DENIED', 'Denied'), ('APPROVED', 'Approved'), ('FLAGGED', 'Flagged')),verbose_name='Comment State')
  amount = models.DecimalField(decimal_places=2,max_digits=20,validators=[positive,nonzero],verbose_name='Donation Amount')
  fee = models.DecimalField(decimal_places=2,max_digits=20,default=Decimal('0.00'),validators=[positive],verbose_name='Donation Fee')
  currency = models.CharField(max_length=8,null=False,blank=False,choices=_currencyChoices,verbose_name='Currency')
  timereceived = models.DateTimeField(verbose_name='Time Received')
  comment = models.TextField(blank=True,verbose_name='Comment')
  modcomment = models.TextField(blank=True,verbose_name='Moderator Comment')
  # Specifies if this donation is a 'test' donation, i.e. generated by a sandbox test, and should not be counted
  testdonation = models.BooleanField(default=False);
  class Meta:
    permissions = (
      ('view_full_list', 'Can view full donation list'),
      ('view_comments', 'Can view all comments'),
      ('view_pending', 'Can view pending doantions'),
      ('view_test', 'Can view test donations'),
    )
    get_latest_by = 'timereceived'
    ordering = [ '-timereceived' ]
    
  def bid_total(self):
    bids |= set(self.challengebid_set.all())|set(self.choicebid_set.all())
    return reduce(lambda a, b: a + b, map(lambda b: b.amount, bids), Decimal('0.00'));

  def clean(self,bid=None):
    super(Donation,self).clean()
    if not self.domainId:
      self.domainId = str(calendar.timegm(self.timereceived.timetuple())) + self.donor.email
    # by default, set the donation currency to the paypal currency
    if not self.currency and self.event:
      self.currency = self.event.paypalcurrency;
    bids = set()
    if bid: bids |= set([bid])
    bids |= set(self.challengebid_set.all())|set(self.choicebid_set.all())
    bids = map(lambda b: b.amount,bids)
    bidtotal = reduce(lambda a,b: a+b,bids,Decimal('0'))
    if bidtotal > self.amount:
      raise ValidationError('Choice/Challenge Bid total is greater than donation amount: %s > %s' % (bidtotal,self.amount))
  def __unicode__(self):
    return unicode(self.donor) + ' (' + unicode(self.amount) + ') (' + unicode(self.timereceived) + ')'

class Donor(models.Model):
  email = models.EmailField(max_length=128,unique=True,null=False,verbose_name='Contact Email')
  alias = models.CharField(max_length=32,unique=True,null=True,blank=True)
  firstname = models.CharField(max_length=32,blank=True,verbose_name='First Name')
  lastname = models.CharField(max_length=32,blank=True,verbose_name='Last Name')
  visibility = models.CharField(max_length=32, null=False, blank=False, default='ANON', choices=(('FULL', 'Fully Visible'), ('ALIAS', 'Alias Only'), ('ANON', 'Anonymous')));
  
  # Address information, yay!
  addresscity = models.CharField(max_length=128,blank=True,null=False,verbose_name='City');
  addressstreet = models.CharField(max_length=128,blank=True,null=False,verbose_name='Street/P.O. Box');
  addressstate = models.CharField(max_length=128,blank=True,null=False,verbose_name='State/Province');
  addresszip = models.CharField(max_length=128,blank=True,null=False,verbose_name='Zip/Postal Code');
  addresscountry = models.CharField(max_length=128,blank=True,null=False,verbose_name='Country');
  
  # Donor specific info
  paypalemail = models.EmailField(max_length=128,unique=True,null=True,blank=True,verbose_name='Paypal Email')
  
  # Runner info
  runneryoutube = models.CharField(max_length=128,unique=True,blank=True,null=True,verbose_name='Youtube Account');
  runnertwitch = models.CharField(max_length=128,unique=True,blank=True,null=True,verbose_name='Twitch Account');
  runnertwitter = models.CharField(max_length=128,unique=True,blank=True,null=True,verbose_name='Twitter Account');
  
  # Prize contributor info
  prizecontributoremail = models.EmailField(max_length=128,unique=True,blank=True,null=True,verbose_name='Contact Email');
  prizecontributorwebsite = models.URLField(blank=True,null=True,verbose_name='Personal Website');
  
  class Meta:
    permissions = (
      ('view_usernames', 'Can view full usernames'),
      ('view_emails', 'Can view email addresses'),
    )
    ordering = ['lastname', 'firstname', 'email']
  def clean(self):
    # an empty value means a null value
    if emptyString(self.alias):
      self.alias = None;
    if emptyString(self.paypalemail):
      self.paypalemail = None;
    # default the contact email to the paypal e-mail if not otherwise specified
    if not self.email and self.paypalemail:
      self.email = self.paypalemail;
    if self.visibility == 'ALIAS' and not self.alias:
      raise ValidationError("Cannot set Donor visibility to 'Alias Only' without an alias");
    if emptyString(self.runneryoutube):
      self.runneryoutube = None;
    if emptyString(self.runnertwitch):
      self.runnertwitch = None;
    if emptyString(self.runnertwitter):
      self.runnertwitter = None;
    if emptyString(self.prizecontributoremail):
      self.prizecontributoremail = None;
    if emptyString(self.prizecontributorwebsite):
      self.prizecontributorwebsite = None;
  def full(self):
    return unicode(self.email) + ' (' + unicode(self) + ')'
  def __unicode__(self):
    if emptyString(self.lastname) and emptyString(self.firstname):
      return '(No Name)' if emptyString(self.alias) else unicode(self.alias);
    ret = unicode(self.lastname) + ', ' + unicode(self.firstname)
    if not emptyString(self.alias):
      ret += ' (' + unicode(self.alias) + ')'
    return ret

class Prize(models.Model):
  name = models.CharField(max_length=64,unique=True)
  category = models.ForeignKey('PrizeCategory',null=True,blank=True)
  sortkey = models.IntegerField(default=0,db_index=True)
  image = models.URLField(max_length=1024,null=True,blank=True)
  description = models.TextField(max_length=1024,null=True,blank=True)
  minimumbid = models.DecimalField(decimal_places=2,max_digits=20,default=Decimal('5.0'),verbose_name='Minimum Bid',validators=[positive,nonzero])
  maximumbid = models.DecimalField(decimal_places=2,max_digits=20,default=Decimal('5.0'),verbose_name='Maximum Bid',validators=[positive,nonzero])
  sumdonations = models.BooleanField(verbose_name='Sum Donations')
  randomdraw = models.BooleanField(default=True,verbose_name='Random Draw')
  event = models.ForeignKey('Event')
  startrun = models.ForeignKey('SpeedRun',related_name='prize_start',null=True,blank=True,verbose_name='Start Run')
  endrun = models.ForeignKey('SpeedRun',related_name='prize_end',null=True,blank=True,verbose_name='End Run')
  starttime = models.DateTimeField(null=True,blank=True,verbose_name='Start Time')
  endtime = models.DateTimeField(null=True,blank=True,verbose_name='End Time')
  winner = models.ForeignKey('Donor',null=True,blank=True)
  deprecated_provided = models.CharField(max_length=64,blank=True,verbose_name='*DEPRECATED* Provided By') # Deprecated
  contributors = models.ManyToManyField('Donor', related_name='prizescontributed');
  emailsent = models.BooleanField(default=False, verbose_name='Email Sent')
  class Meta:
    ordering = [ 'event__date', 'sortkey', 'name' ]
    unique_together = ( 'category', 'winner', 'event' )
  def __unicode__(self):
    return unicode(self.name)
  def clean(self):
    if (not self.startrun) != (not self.endrun):
      raise ValidationError('Must have both Start Run and End Run set, or neither')
    if self.startrun and self.event != self.startrun.event:
      raise ValidationError('Prize Event must be the same as Start Run Event')
    if self.endrun and self.event != self.endrun.event:
      raise ValidationError('Prize Event must be the same as End Run Event')
    if self.startrun and self.startrun.sortkey > self.endrun.sortkey:
      raise ValidationError('Start Run must have a lesser sortkey than End Run')
    if (not self.starttime) != (not self.endtime):
      raise ValidationError('Must have both Start Run and End Run set, or neither')
    if self.starttime and self.starttime > self.endtime:
      raise ValidationError('Prize Start Time must be later than End Time')
    if self.startrun and self.starttime:
      raise ValidationError('Cannot have both Start/End Run and Start/End Time set')
    if self.maximumbid < self.minimumbid:
      raise ValidationError('Maximum Bid cannot be lower than Minimum Bid')
    if not self.sumdonations and self.maximumbid != self.minimumbid:
      raise ValidationError('Maximum Bid cannot differ from Minimum Bid if Sum Donations is not checked')
  def eligibledonors(self):
    qs = Donation.objects.filter(event=self.event,transactionstate='COMPLETED').select_related('donor')
    qs = qs.exclude(donor__prize__category=self.category, donor__prize__event=self.event);
    if self.startrun:
      qs = qs.filter(timereceived__gte=self.startrun.starttime,timereceived__lte=self.endrun.endtime)
    if self.starttime:
      qs = qs.filter(timereceived__gte=self.starttime,timereceived__lte=self.endtime)
    donors = {}
    for d in qs:
      if self.sumdonations:
        donors.setdefault(d.donor, Decimal('0.0'))
        donors[d.donor] += d.amount
      else:
        donors[d.donor] = max(d.amount,donors.get(d.donor,Decimal('0.0')))
    if not donors:
      return []
    elif self.randomdraw:
      def weight(mn,mx,a):
        if a < mn: return 0.0
        if a > mx: return float(mx/mn)
        return float(a/mn)
      return sorted(filter(lambda d: d['weight'] >= 1.0,map(lambda d: {'donor':d[0].id,'amount':d[1],'weight':weight(self.minimumbid,self.maximumbid,d[1])}, donors.items())),key=lambda d: d['donor'])
    else:
      m = max(donors.items(), key=lambda d: d[1])
      return [{'donor':m[0].id,'amount':m[1],'weight':1.0}]

class PrizeCategory(models.Model):
  name = models.CharField(max_length=64,unique=True)
  class Meta:
    verbose_name = 'Prize Category'
    verbose_name_plural = 'Prize Categories'
  def __unicode__(self):
    return self.name

class SpeedRun(models.Model):
  name = models.CharField(max_length=64)
  deprecated_runners = models.CharField(max_length=1024,blank=True,verbose_name='*DEPRECATED* Runners') # This field is now deprecated, we should eventually set up a way to migrate the old set-up to use the donor links
  sortkey = models.IntegerField(db_index=True,verbose_name='Sort Key')
  description = models.TextField(max_length=1024,blank=True)
  event = models.ForeignKey('Event')
  starttime = models.DateTimeField(verbose_name='Start Time')
  endtime = models.DateTimeField(verbose_name='End Time')
  runners = models.ManyToManyField('Donor');
  class Meta:
    verbose_name = 'Speed Run';
    unique_together = ( 'name','event' );
    ordering = [ 'event__date', 'sortkey', 'starttime' ];
  def __unicode__(self):
    return u'%s (%s)' % (self.name,self.event)

class UserProfile(models.Model):
  user = models.ForeignKey(User, unique=True)
  prepend = models.CharField('Template Prepend', max_length=64,blank=True)
  class Meta:
    verbose_name = 'User Profile'
    permissions = (
      ('show_rendertime', 'Can view page render times'),
      ('show_queries', 'Can view database queries'),
      ('sync_schedule', 'Can sync the schedule'),
      ('can_search', 'Can use search url'),
    )
  def __unicode__(self):
    return unicode(self.user)

