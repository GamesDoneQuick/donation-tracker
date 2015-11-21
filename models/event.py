import re
import datetime

from django.db import models
from django.core.exceptions import ValidationError
from django.db.utils import OperationalError
from django.core import validators
import post_office.models
from ..validators import *
from oauth2client.django_orm import FlowField,CredentialsField
from oauth2client.client import OAuth2WebServerFlow
import pytz
from timezone_field import TimeZoneField

__all__ = [
  'FlowModel',
  'CredentialsModel',
  'Event',
  'PostbackURL',
  'SpeedRun',
  'Runner',
  'Submission',
]

_timezoneChoices = list(map(lambda x: (x,x), pytz.common_timezones))
_currencyChoices = (('USD','US Dollars'),('CAD', 'Canadian Dollars'))


class FlowModel(models.Model):
  id = models.OneToOneField('auth.User', primary_key=True)
  flow = FlowField()
  class Meta:
    app_label = 'tracker'


class CredentialsModel(models.Model):
  id = models.OneToOneField('auth.User', primary_key=True)
  credentials = CredentialsField()
  class Meta:
    app_label = 'tracker'


class TimestampValidator(validators.RegexValidator):
  regex = r'(?:(?:(\d+):)?(?:(\d+):))?(\d+)(?:\.(\d{1,3}))?$'
  def __call__(self, value):
    super(TimestampValidator, self).__call__(value)
    h,m,s,ms = re.match(self.regex, unicode(value)).groups()
    if h is not None and int(m) >= 60:
      raise ValidationError('Minutes cannot be 60 or higher if the hour part is specified')
    if m is not None and int(s) >= 60:
      raise ValidationError('Seconds cannot be 60 or higher if the minute part is specified')


class TimestampField(models.Field):
  __metaclass__ = models.SubfieldBase
  default_validators = [TimestampValidator()]
  match_string = re.compile(r'(?:(?:(\d+):)?(?:(\d+):))?(\d+)(?:\.(\d+))?')

  def __init__(self, always_show_h=False, always_show_m=False, always_show_ms=False, *args, **kwargs):
    super(TimestampField, self).__init__(*args, **kwargs)
    self.always_show_h = always_show_h
    self.always_show_m = always_show_m
    self.always_show_ms = always_show_ms

  def to_python(self, value):
    if isinstance(value, basestring):
      try:
        value = TimestampField.time_string_to_int(value)
      except ValueError:
        return value
    if not value:
      return 0
    h,m,s,ms = value / 3600000, value / 60000 % 60, value / 1000 % 60, value % 1000
    if h or self.always_show_h:
      if ms or self.always_show_ms:
        return '%d:%02d:%02d.%03d' % (h, m, s, ms)
      else:
        return '%d:%02d:%02d' % (h, m, s)
    elif m or self.always_show_m:
      if ms or self.always_show_ms:
        return '%d:%02d.%03d' % (m, s, ms)
      else:
        return '%d:%02d' % (m, s)
    else:
      if ms or self.always_show_ms:
        return '%d.%03d' % (s, ms)
      else:
        return '%d' % s

  @staticmethod
  def time_string_to_int(value):
    try:
      if str(int(value)) == value:
        return int(value) * 1000
    except ValueError:
      pass
    if not isinstance(value, basestring):
      return value
    if not value: return 0
    match = TimestampField.match_string.match(value)
    if not match:
      raise ValueError('Not a valid timestamp: ' + value)
    h,m,s,ms = match.groups()
    s = int(s)
    m = int(m or s / 60)
    s %= 60
    h = int(h or m / 60)
    m %= 60
    ms = int(ms or 0)
    return h * 3600000 + m * 60000 + s * 1000 + ms

  def pre_save(self, model, add):
    return TimestampField.time_string_to_int(getattr(model, self.attname))

  def get_internal_type(self):
    return 'IntegerField'

  def validate(self, value, model_instance):
    super(TimestampField, self).validate(value, model_instance)
    try:
      TimestampField.time_string_to_int(value)
    except ValueError:
      raise ValidationError('Not a valid timestamp')


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
  timezone = TimeZoneField(default='US/Eastern')
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

  def start_push_notification(self, request):
    from django.core.urlresolvers import reverse
    approval_force = False
    try:
      credentials = CredentialsModel.objects.get(id=request.user).credentials
      if credentials:
        if not credentials.refresh_token:
          approval_force = True
          raise CredentialsModel.DoesNotExist
        elif credentials.access_token_expired:
          import httplib2
          credentials.refresh(httplib2.Http())
    except CredentialsModel.DoesNotExist:
      from django.conf import settings
      from django.http import HttpResponseRedirect
      FlowModel.objects.filter(id=request.user).delete()
      kwargs = {}
      if approval_force:
        kwargs['approval_prompt'] = 'force'
      defaultflow = OAuth2WebServerFlow(client_id=settings.GOOGLE_CLIENT_ID,
                                        client_secret=settings.GOOGLE_CLIENT_SECRET,
                                        scope='https://www.googleapis.com/auth/drive.metadata.readonly',
                                        redirect_uri=request.build_absolute_uri(reverse('admin:google_flow')).replace('/cutler5:','/cutler5.example.com:'),
                                        access_type='offline',
                                        **kwargs)
      flow = FlowModel(id=request.user,flow=defaultflow)
      flow.save()
      url = flow.flow.step1_get_authorize_url()
      return HttpResponseRedirect(url)
    from apiclient.discovery import build
    import httplib2
    import uuid
    import time
    drive = build('drive', 'v2', credentials.authorize(httplib2.Http()))
    body = {
        'kind': 'api#channel',
        'resourceId': self.scheduleid,
        'id': unicode(uuid.uuid4()),
        'token': u'%s:%s' % (self.id, unicode(request.user)),
        'type': 'web_hook',
        'address': request.build_absolute_uri(reverse('tracker.views.refresh_schedule')),
        'expiration': int(time.time() + 24*60*60) * 1000 # approx one day
    }
    try:
        drive.files().watch(fileId=self.scheduleid, body=body).execute()
    except Exception as e:
        from django.contrib import messages

        messages.error(request, u'Could not start push notification: %s' % e)
        return False
    return True

  class Meta:
    app_label = 'tracker'
    get_latest_by = 'date'
    permissions = (
      ('can_edit_locked_events', 'Can edit locked events'),
    )
    ordering = ('date',)


def LatestEvent():
  try:
    return Event.objects.latest()
  except (Event.DoesNotExist, OperationalError):
    return None

class PostbackURL(models.Model):
  event = models.ForeignKey('Event', on_delete=models.PROTECT, verbose_name='Event', null=False, blank=False, related_name='postbacks')
  url = models.URLField(blank=False,null=False,verbose_name='URL')
  class Meta:
    app_label = 'tracker'


class SpeedRunManager(models.Manager):
  def get_by_natural_key(self, name, event):
    return self.get(name=name,event=Event.objects.get_by_natural_key(*event))

  def get_or_create_by_natural_key(self, name, event):
    return self.get_or_create(name=name, event=Event.objects.get_by_natural_key(*event))


def runners_exists(runners):
  for r in runners.split(','):
    try:
      Runner.objects.get_by_natural_key(r.strip())
    except Runner.DoesNotExist:
      raise ValidationError('Runner not found: "%s"' % r.strip())

class SpeedRun(models.Model):
  objects = SpeedRunManager()
  event = models.ForeignKey('Event', on_delete=models.PROTECT, default=LatestEvent)
  name = models.CharField(max_length=64)
  deprecated_runners = models.CharField(max_length=1024, blank=True, verbose_name='*DEPRECATED* Runners', editable=False, validators=[runners_exists]) # This field is now deprecated, we should eventually set up a way to migrate the old set-up to use the donor links
  console = models.CharField(max_length=32,blank=True)
  commentators = models.CharField(max_length=1024,blank=True)
  description = models.TextField(max_length=1024,blank=True)
  starttime = models.DateTimeField(verbose_name='Start Time', editable=False, null=True)
  endtime = models.DateTimeField(verbose_name='End Time', editable=False, null=True)
  order = models.IntegerField(editable=False, null=True)  # can be temporarily null when moving runs around, or null when they haven't been slotted in yet
  run_time = TimestampField(always_show_h=True)
  setup_time = TimestampField(always_show_h=True)
  runners = models.ManyToManyField('Runner')

  class Meta:
    app_label = 'tracker'
    verbose_name = 'Speed Run'
    unique_together = (( 'name','event' ), ('event', 'order'))
    ordering = [ 'event__date', 'order' ]

  def natural_key(self):
    return (self.name,self.event.natural_key())

  def clean(self):
    if not self.name:
      raise ValidationError('Name cannot be blank')

  def save(self, fix_time=True, fix_runners=True, *args, **kwargs):
    can_fix_time = self.order and self.run_time and self.setup_time
    i = TimestampField.time_string_to_int

    # fix our own time
    if fix_time and can_fix_time:
      prev = SpeedRun.objects.filter(event=self.event, order__lt=self.order).last()
      if prev:
        self.starttime = prev.starttime + datetime.timedelta(milliseconds=i(prev.run_time)+i(prev.setup_time))
      else:
        self.starttime = datetime.datetime.combine(self.event.date, datetime.time(12, tzinfo=self.event.timezone))
      self.endtime = self.starttime + datetime.timedelta(milliseconds=i(self.run_time)+i(self.setup_time))

    if fix_runners and self.id:
      if not self.runners.exists():
        try:
          self.runners.add(*[Runner.objects.get_by_natural_key(r.strip()) for r in self.deprecated_runners.split(',')])
        except Runner.DoesNotExist:
          pass
      if self.runners.exists():
        self.deprecated_runners = u', '.join(unicode(r) for r in self.runners.all())

    super(SpeedRun, self).save(*args, **kwargs)

    # fix up all the others if requested
    if fix_time:
      if can_fix_time:
        next = SpeedRun.objects.filter(event=self.event, order__gt=self.order).first()
        starttime = self.starttime + datetime.timedelta(milliseconds=i(self.run_time)+i(self.setup_time))
        if next and next.starttime != starttime:
          return [self] + next.save(*args, **kwargs)
      elif self.starttime:
        prev = SpeedRun.objects.filter(event=self.event, starttime__lte=self.starttime).exclude(order=None).last()
        if prev:
          starttime = prev.starttime + datetime.timedelta(milliseconds=i(prev.run_time)+i(prev.setup_time))
        else:
          starttime = datetime.datetime.combine(self.event.date, datetime.time(12, tzinfo=self.event.timezone))
        next = SpeedRun.objects.filter(event=self.event, starttime__gte=self.starttime).exclude(order=None).first()
        if next and next.starttime != starttime:
          return [self] + next.save(*args, **kwargs)
    return [self]

  def __unicode__(self):
    return u'%s (%s)' % (self.name,self.event)


class Runner(models.Model):
  class _Manager(models.Manager):
    def get_by_natural_key(self, name):
      return self.get(name=name)

    def get_or_create_by_natural_key(self, name):
      return self.get_or_create(name=name)

  class Meta:
    app_label = 'tracker'

  objects = _Manager()
  name = models.CharField(max_length=64,unique=True)
  stream = models.URLField(max_length=128, blank=True)
  twitter = models.SlugField(max_length=15, blank=True)
  youtube = models.SlugField(max_length=20, blank=True)
  donor = models.OneToOneField('tracker.Donor', blank=True, null=True)

  def natural_key(self):
    return (self.name,)

  def __unicode__(self):
    return self.name


class Submission(models.Model):
  class Meta:
    app_label = 'tracker'

  external_id = models.IntegerField(primary_key=True)
  run = models.ForeignKey('SpeedRun')
  runner = models.ForeignKey('Runner')
  game_name = models.TextField(max_length=64)
  category = models.TextField(max_length=32)
  console = models.TextField(max_length=32)
  estimate = TimestampField(always_show_h=True)

  def __unicode__(self):
    return '%s (%s) by %s' % (self.game_name, self.category, self.runner)

  def save(self, *args, **kwargs):
    super(Submission, self).save(*args, **kwargs)
    ret = [self]
    save_run = False
    if not self.run.description:
      self.run.description = self.category
      save_run = True
    if not self.run.console:
      self.run.console = self.console
      save_run = True
    if not self.run.run_time:
      self.run.run_time = self.estimate
      save_run = True
    if save_run:
      self.run.save()
      ret.append(self.run)
    return ret
