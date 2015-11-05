from django.db import models
from django.db.utils import OperationalError
from django.contrib.auth.models import User
from tracker.validators import *

from event import *
from bid import *
from donation import *
from prize import *

__all__ = [
    'FlowModel',
    'CredentialsModel',
    'Event',
    'PostbackURL',
    'Bid',
    'DonationBid',
    'BidSuggestion',
    'Donation',
    'Donor',
    'DonorCache',
    'Prize',
    'PrizeCategory',
    'PrizeTicket',
    'PrizeWinner',
    'DonorPrizeEntry',
    'SpeedRun',
    'Runner',
    'Submission',
    'UserProfile',
    'Log',
]

class UserProfile(models.Model):
    user = models.OneToOneField(User)
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

class Log(models.Model):
  timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Timestamp')
  category = models.CharField(max_length=64, default='other', blank=False, null=False, verbose_name='Category')
  message = models.TextField(blank=True, null=False, verbose_name='Message' )
  event = models.ForeignKey('Event', blank=True, null=True, on_delete=models.PROTECT)
  user = models.ForeignKey(User, blank=True, null=True)
  class Meta:
    verbose_name = 'Log'
    permissions = (
      ('can_view_log', 'Can view tracker logs'),
      ('can_change_log', 'Can change tracker logs'),
    )
    ordering = ['-timestamp']
  def __unicode__(self):
    result = unicode(self.timestamp);
    if self.event:
      result += u' (' + self.event.short + u')'
    result += u' -- ' + self.category
    if self.message:
      m = self.message;
      if len(m) > 18:
        m = m[:15] + u'...'
      result += u': ' + m
    return result

