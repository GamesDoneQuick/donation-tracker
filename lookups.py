from ajax_select import LookupChannel
from django.utils.html import escape
from django.db.models import Q

from models import *
import viewutil;
import filters

class GenericLookup(LookupChannel):
	def get_query(self,q,request):
		params = {'q': q};
		event = viewutil.get_selected_event(request);
		if event:
			params['event'] = event.id;
		return filters.run_model_query(self.model, params, user=request.user, mode='admin');

	def get_result(self,obj):
		return unicode(obj)

	def format_match(self,obj):
		return self.format_item_display(obj)

	def format_item_display(self,obj):
		return escape(unicode(obj))

class ChallengeLookup(GenericLookup):
	def __init__(self, *args, **kwargs):
		self.model = Challenge
		super(ChallengeLookup,self).__init__(*args, **kwargs)

class ChoiceLookup(GenericLookup):
	def __init__(self, *args, **kwargs):
		self.model = Choice
		super(ChoiceLookup,self).__init__(*args, **kwargs)

class ChoiceOptionLookup(GenericLookup):
	def __init__(self, *args, **kwargs):
		self.model = ChoiceOption
		super(ChoiceOptionLookup,self).__init__(*args, **kwargs)

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


