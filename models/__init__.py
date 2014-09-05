from django.db import models
from django.db.models import Q
from django.db.models import Sum,Max
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from tracker.validators import *

import calendar
import urllib2
from datetime import datetime
import re
import cld

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