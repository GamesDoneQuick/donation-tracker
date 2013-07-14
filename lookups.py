from ajax_select import LookupChannel
from django.utils.html import escape
from django.db.models import Q

from models import *
import filters

class GenericLookup(LookupChannel):
	def get_query(self,q,request):
		return self.model.objects.filter(filters.model_general_filter(self.model,q,request.user))

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

class DonationLookup(GenericLookup):
	def __init__(self, *args, **kwargs):
		self.model = Donation
		super(DonationLookup,self).__init__(*args, **kwargs)


