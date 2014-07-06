from django.db import models
from django.db.models import Q;
from django.db.models import Sum,Max
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from tracker.validators import *

import calendar
import urllib2
from datetime import datetime
import re;
import cld;

from event import *
from bid import *
from donation import *
from prize import *

__all__ = [
	'Event',
	'PostbackURL',
	'Bid',
	'DonationBid',
	'BidSuggestion',
	'Donation',
	'Donor',
	'Prize',
	'PrizeCategory',
	'PrizeTicket',
	'PrizeWinner',
	'SpeedRun',
	'UserProfile',
]

def LatestEvent():
  try:
    return Event.objects.latest()
  except Event.DoesNotExist:
    return None

class SpeedRun(models.Model):
  name = models.CharField(max_length=64,editable=False)
  deprecated_runners = models.CharField(max_length=1024,blank=True,verbose_name='*DEPRECATED* Runners') # This field is now deprecated, we should eventually set up a way to migrate the old set-up to use the donor links
  sortkey = models.IntegerField(db_index=True,verbose_name='Sort Key')
  description = models.TextField(max_length=1024,blank=True)
  event = models.ForeignKey('Event', default=LatestEvent)
  starttime = models.DateTimeField(verbose_name='Start Time')
  endtime = models.DateTimeField(verbose_name='End Time')
  runners = models.ManyToManyField('Donor', blank=True, null=True);
  class Meta:
    verbose_name = 'Speed Run';
    unique_together = ( 'name','event' );
    ordering = [ 'event__date', 'sortkey', 'starttime' ];
  def clean(self):
	if not self.name:
	  raise ValidationError('Name cannot be blank')
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