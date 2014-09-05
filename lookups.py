from ajax_select import LookupChannel
from django.utils.html import escape
from django.db.models import Q

from models import *
import viewutil
import filters

"""
In order to use these lookups properly with the admin, you will need to install/enable the 'ajax_select'
django module, and also add this block to the settings.py file:

AJAX_LOOKUP_CHANNELS = {
  'donation'     : ('tracker.lookups', 'DonationLookup'),
  'donor'        : ('tracker.lookups', 'DonorLookup'),
  'run'          : ('tracker.lookups', 'RunLookup'),
  'event'        : ('tracker.lookups', 'EventLookup'),
  'bidtarget'    : ('tracker.lookups', 'BidTargetLookup'),
  'bid'          : ('tracker.lookups', 'BidLookup'),
  'allbids'      : ('tracker.lookups', 'AllBidLookup'),
  'prize'        : ('tracker.lookups', 'PrizeLookup'),
}
"""

class GenericLookup(LookupChannel):
  def get_query(self,q,request):
    params = {'q': q}
    event = viewutil.get_selected_event(request)
    if event and self.useEvent:
      params['event'] = event.id
    model = self.model
    if hasattr(self, 'modelName'):
      model = self.modelName
    if self.useLock and not request.user.has_perm('tracker.can_edit_locked_events'):
      params['locked'] = False
    return filters.run_model_query(model, params, user=request.user, mode='admin')

  def get_result(self,obj):
    return unicode(obj)
    
  def format_match(self,obj):
    return self.format_item_display(obj)

  def format_item_display(self,obj):
    return escape(unicode(obj))

class BidLookup(GenericLookup):
  def __init__(self, *args, **kwargs):
    self.model = Bid
    self.modelName = 'bid'
    self.useEvent = True
    self.useLock = True
    super(BidLookup,self).__init__(*args, **kwargs)
    
class AllBidLookup(GenericLookup):
  def __init__(self, *args, **kwargs):
    self.model = Bid
    self.modelName = 'allbids'
    self.useEvent = True
    self.useLock = True
    super(AllBidLookup,self).__init__(*args, **kwargs)

class BidTargetLookup(GenericLookup):
  def __init__(self, *args, **kwargs):
    self.model = Bid
    self.modelName = 'bidtarget'
    self.useEvent = True
    self.useLock = True
    super(BidTargetLookup,self).__init__(*args, **kwargs)

class DonationLookup(GenericLookup):
  def __init__(self, *args, **kwargs):
    self.model = Donation
    self.useEvent = True
    self.useLock = True
    super(DonationLookup,self).__init__(*args, **kwargs)

class DonorLookup(GenericLookup):
  def __init__(self, *args, **kwargs):
    self.model = Donor
    self.useEvent = False
    self.useLock = False
    super(DonorLookup,self).__init__(*args, **kwargs)

class PrizeLookup(GenericLookup):
  def __init__(self, *args, **kwargs):
    self.model = Prize
    self.useEvent = True
    self.useLock = False
    super(PrizeLookup,self).__init__(*args, **kwargs)

class RunLookup(GenericLookup):
  def __init__(self, *args, **kwargs):
    self.model = SpeedRun
    self.useEvent = True
    self.useLock = True
    super(RunLookup,self).__init__(*args, **kwargs)

class EventLookup(GenericLookup):
  def __init__(self, *args, **kwargs):
    self.model = Event
    self.useEvent = False
    self.useLock = True
    super(EventLookup,self).__init__(*args, **kwargs)
