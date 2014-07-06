from django.db import models
from django.core.exceptions import ValidationError

from tracker.validators import *
import pytz;
import re

__all__ = [
  'Event',
  'PostbackURL',
]

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
  scheduleid = models.CharField(max_length=128,unique=True,null=True,blank=True, verbose_name='Schedule ID')
  scheduletimezone = models.CharField(max_length=64,blank=True,choices=_timezoneChoices, default='US/Eastern', verbose_name='Schedule Timezone');
  scheduledatetimefield = models.CharField(max_length=128,blank=True, verbose_name='Schedule Datetime')
  schedulegamefield = models.CharField(max_length=128,blank=True, verbose_name='Schdule Game')
  schedulerunnersfield = models.CharField(max_length=128,blank=True, verbose_name='Schedule Runners')
  scheduleestimatefield = models.CharField(max_length=128,blank=True, verbose_name='Schedule Estimate')
  schedulesetupfield = models.CharField(max_length=128,blank=True, verbose_name='Schedule Setup')
  schedulecommentatorsfield = models.CharField(max_length=128,blank=True,verbose_name='Schedule Commentators')
  schedulecommentsfield = models.CharField(max_length=128,blank=True,verbose_name='Schedule Comments')
  date = models.DateField()
  prizemailsubject = models.CharField(max_length=128, blank=False, null=False, default='', verbose_name="Prize Email Subject Line")
  prizemailbody = models.TextField(blank=False, null=False, default='', verbose_name="Prize Email Body")
  locked = models.BooleanField(default=False,help_text='Requires special permission to edit this event or anything associated with it')
  def __unicode__(self):
    return self.name
  def clean(self):
    if self.id and self.id < 1:
      raise ValidationError('Event ID must be positive and non-zero')
    if not re.match('^\w+$', self.short):
      raise ValidationError('Event short name must be a url-safe string');
    if not self.scheduleid:
      self.scheduleid = None;
  class Meta:
    app_label = 'tracker'
    get_latest_by = 'date'
    permissions = (
      ('can_edit_locked_events', 'Can edit locked events'),
    )

class PostbackURL(models.Model):
  event = models.ForeignKey('Event', verbose_name='Event', null=False, blank=False, related_name='postbacks');
  url = models.URLField(blank=False,null=False,verbose_name='URL');
  class Meta:
    app_label = 'tracker'
      
