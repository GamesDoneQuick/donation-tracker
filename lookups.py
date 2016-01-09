from ajax_select import LookupChannel
from django.utils.html import escape
from django.db.models import Q
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

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
  'runner'       : ('tracker.lookups', 'RunnerLookup'),
  'country'      : ('tracker.lookups', 'CountryLookup'),
}
"""

class CountryLookup(LookupChannel):
    def __init__(self, *args, **kwargs):
        self.model = Country
        super(CountryLookup,self).__init__(*args, **kwargs)
        
    def get_query(self, q, request):
        return Country.objects.filter(name__icontains=q)
        
    def get_result(self,obj):
        return unicode(obj)
        
    def format_match(self,obj):
        return escape(unicode(obj))
        
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
    return escape(unicode(obj))

  # returning the admin URL reduces the genericity of our solution a little bit, but this can be solved
  # by using distinct lookups for admin/non-admin applications (which we should do regardless since
  # non-admin search should be different)
  def format_item_display(self,obj):
    result = u'<a href="{0}">{1}</a>'.format(reverse('admin:tracker_{0}_change'.format(obj._meta.model_name),args=[obj.pk]), escape(unicode(obj)))
    return mark_safe(result);

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

class RunnerLookup(GenericLookup):
  def __init__(self, *args, **kwargs):
    self.model = Runner
    self.useEvent = False
    self.useLock = False
    super(RunnerLookup,self).__init__(*args, **kwargs)