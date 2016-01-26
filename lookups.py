from ajax_select import LookupChannel
from django.utils.html import escape
from django.db.models import Q
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.contrib.auth import get_user_model

from tracker.models import *
import tracker.viewutil as viewutil
import tracker.filters as filters

"""
In order to use these lookups properly with the admin, you will need to install/enable the 'ajax_select'
django module, and also add an AJAX_LOOKUP_CHANNELS table (the table of all
lookups used by this application are in tracker/ajax_lookup_channels.py)

They can be imported with the line:

from tracker.ajax_lookup_channels import AJAX_LOOKUP_CHANNELS
"""

class UserLookup(LookupChannel):
    def __init__(self, *args, **kwargs):
        self.model = get_user_model()
        super(UserLookup,self).__init__(*args, **kwargs)
    
    def get_query(self, q, request):
        return self.model.objects.filter(username__icontains=q)
        
    def get_result(self, obj):
        return obj.username
    
    def format_match(self,obj):
        return escape(obj.username)
    
    def can_add(self, user, source_model):
        # avoid in-line addition of users by accident
        return False
        
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
    
    def can_add(self, user, source_model):
        # Presumably, we don't want to add countries typically
        return False

class CountryRegionLookup(LookupChannel):
    def __init__(self, *args, **kwargs):
        self.model = CountryRegion
        super(CountryRegionLookup, self).__init__(*args, **kwargs)

    def get_query(self, q, request):
        return CountryRegion.objects.filter(Q(name__icontains=q)|Q(country__name__icontains=q))

    def get_result(self, obj):
        return unicode(obj)

    def format_match(self, obj):
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
