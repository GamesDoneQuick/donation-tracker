from ajax_select import LookupChannel
from django.utils.html import escape
from django.db.models import Q

from models import *
import viewutil;
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
};
"""

class GenericLookup(LookupChannel):
  def get_query(self,q,request):
    params = {'q': q};
    event = viewutil.get_selected_event(request);
    if event:
      params['event'] = event.id;
    model = self.model;
    if hasattr(self, 'modelName'):
      model = self.modelName;
    return filters.run_model_query(model, params, user=request.user, mode='admin');

  def get_result(self,obj):
    return unicode(obj)
    
  def format_match(self,obj):
    return self.format_item_display(obj)

  def format_item_display(self,obj):
    return escape(unicode(obj))

class BidLookup(GenericLookup):
  def __init__(self, *args, **kwargs):
    self.model = Bid;
    self.modelName = 'bid';
    super(BidLookup,self).__init__(*args, **kwargs)
    
class AllBidLookup(GenericLookup):
  def __init__(self, *args, **kwargs):
    self.model = Bid;
    self.modelName = 'allbids';
    super(AllBidLookup,self).__init__(*args, **kwargs)

class BidTargetLookup(GenericLookup):
  def __init__(self, *args, **kwargs):
    self.model = Bid;
    self.modelName = 'bidtarget';
    super(BidTargetLookup,self).__init__(*args, **kwargs)

class DonationLookup(GenericLookup):
  def __init__(self, *args, **kwargs):
    self.model = Donation
    super(DonationLookup,self).__init__(*args, **kwargs)

class DonorLookup(GenericLookup):
  def __init__(self, *args, **kwargs):
    self.model = Donor
    super(DonorLookup,self).__init__(*args, **kwargs)

class PrizeLookup(GenericLookup):
  def __init__(self, *args, **kwargs):
    self.model = Prize
    super(PrizeLookup,self).__init__(*args, **kwargs)

class RunLookup(GenericLookup):
  def __init__(self, *args, **kwargs):
    self.model = SpeedRun
    super(RunLookup,self).__init__(*args, **kwargs)

class EventLookup(GenericLookup):
  def __init__(self, *args, **kwargs):
    self.model = Event
    super(EventLookup,self).__init__(*args, **kwargs)
