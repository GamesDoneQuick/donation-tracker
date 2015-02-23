from django.db import models
from django.core.exceptions import ValidationError

import post_office.models

from tracker.validators import *

from decimal import Decimal

import pytz
import re

__all__ = [
  'Event',
  'PostbackURL',
  'SpeedRun',
]

_timezoneChoices = list(map(lambda x: (x,x), pytz.common_timezones))
_currencyChoices = (('USD','US Dollars'),('CAD', 'Canadian Dollars'))

def LatestEvent():
  try:
    return Event.objects.latest()
  except Event.DoesNotExist:
    return None


class EventManager(models.Manager):
  def get_by_natural_key(self, short):
    return self.get(short=short)

class Event(models.Model):
  objects = EventManager()
  short = models.CharField(max_length=64,unique=True)
  name = models.CharField(max_length=128)
  receivername = models.CharField(max_length=128,blank=True,null=False,verbose_name='Receiver Name')
  targetamount = models.DecimalField(decimal_places=2,max_digits=20,validators=[positive,nonzero],verbose_name='Target Amount')
  usepaypalsandbox = models.BooleanField(default=False,verbose_name='Use Paypal Sandbox')
  paypalemail = models.EmailField(max_length=128,null=False,blank=False, verbose_name='Receiver Paypal')
  paypalcurrency = models.CharField(max_length=8,null=False,blank=False,default=_currencyChoices[0][0],choices=_currencyChoices, verbose_name='Currency')
  donationemailtemplate = models.ForeignKey(post_office.models.EmailTemplate, verbose_name='Donation Email Template', default=None, null=True, blank=True, on_delete=models.PROTECT, related_name='event_donation_templates')
  pendingdonationemailtemplate = models.ForeignKey(post_office.models.EmailTemplate, verbose_name='Pending Donation Email Template', default=None, null=True, blank=True, on_delete=models.PROTECT, related_name='event_pending_donation_templates')
  donationemailsender = models.EmailField(max_length=128, null=True, blank=True, verbose_name='Donation Email Sender')
  scheduleid = models.CharField(max_length=128,unique=True,null=True,blank=True, verbose_name='Schedule ID')
  scheduletimezone = models.CharField(max_length=64,blank=True,choices=_timezoneChoices, default='US/Eastern', verbose_name='Schedule Timezone')
  scheduledatetimefield = models.CharField(max_length=128,blank=True, verbose_name='Schedule Datetime')
  schedulegamefield = models.CharField(max_length=128,blank=True, verbose_name='Schdule Game')
  schedulerunnersfield = models.CharField(max_length=128,blank=True, verbose_name='Schedule Runners')
  scheduleestimatefield = models.CharField(max_length=128,blank=True, verbose_name='Schedule Estimate')
  schedulesetupfield = models.CharField(max_length=128,blank=True, verbose_name='Schedule Setup')
  schedulecommentatorsfield = models.CharField(max_length=128,blank=True,verbose_name='Schedule Commentators')
  schedulecommentsfield = models.CharField(max_length=128,blank=True,verbose_name='Schedule Comments')
  date = models.DateField()
  locked = models.BooleanField(default=False,help_text='Requires special permission to edit this event or anything associated with it')
  def __unicode__(self):
    return self.name
  def natural_key(self):
    return self.short
  def clean(self):
    if self.id and self.id < 1:
      raise ValidationError('Event ID must be positive and non-zero')
    if not re.match('^\w+$', self.short):
      raise ValidationError('Event short name must be a url-safe string')
    if not self.scheduleid:
      self.scheduleid = None
    if self.donationemailtemplate != None or self.pendingdonationemailtemplate != None:
      if not self.donationemailsender:
        raise ValidationError('Must specify a donation email sender if automailing is used')
  class Meta:
    app_label = 'tracker'
    get_latest_by = 'date'
    permissions = (
      ('can_edit_locked_events', 'Can edit locked events'),
    )
    ordering = ('date',)

class PostbackURL(models.Model):
  event = models.ForeignKey('Event', verbose_name='Event', null=False, blank=False, related_name='postbacks')
  url = models.URLField(blank=False,null=False,verbose_name='URL')
  class Meta:
    app_label = 'tracker'

class SpeedRunManager(models.Manager):
  def get_by_natural_key(self, name, event):
    return self.get(name=name,event=Event.objects.get_by_natural_key(*event))

class SpeedRun(models.Model):
  objects = SpeedRunManager()
  event = models.ForeignKey('Event', default=LatestEvent)
  name = models.CharField(max_length=64,editable=False)
  deprecated_runners = models.CharField(max_length=1024,blank=True,verbose_name='*DEPRECATED* Runners') # This field is now deprecated, we should eventually set up a way to migrate the old set-up to use the donor links
  description = models.TextField(max_length=1024,blank=True)
  starttime = models.DateTimeField(verbose_name='Start Time')
  endtime = models.DateTimeField(verbose_name='End Time')
  runners = models.ManyToManyField('Donor', blank=True, null=True)
  class Meta:
    app_label = 'tracker'
    verbose_name = 'Speed Run'
    unique_together = ( 'name','event' )
    ordering = [ 'event__date', 'starttime' ]
  def natural_key(self):
    return (self.name,self.event.natural_key())
  def clean(self):
	if not self.name:
	  raise ValidationError('Name cannot be blank')
  def __unicode__(self):
    return u'%s (%s)' % (self.name,self.event)
