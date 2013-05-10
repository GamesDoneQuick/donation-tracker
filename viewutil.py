import re;
from tracker.models import *;
import filters;
from django.db.models import Count,Sum,Max,Avg,Q

# Adapted from http://djangosnippets.org/snippets/1474/

def get_referer_site(request):
  origin = request.META.get('HTTP_ORIGIN', None);
  if origin != None:
    return re.sub('^https?:\/\/', '', origin);
  else:
    return None;
    
def get_event(event):
	if event:
		if re.match('^\d+$', event):
			event = int(event)
			return Event.objects.get(id=event)
		else:
			eventSet = Event.objects.filter(short=event);
			if eventSet.exists():
				return eventSet[0];
			else:
				raise Http404;	
	e = Event()
	e.id = '' 
	e.name = 'All Events'
	return e

_1ToManyBidsAggregateFilter = Q(bids__donation__transactionstate='COMPLETED');
_1ToManyDonationAggregateFilter = Q(donation__transactionstate='COMPLETED');
ChoiceBidAggregateFilter = _1ToManyDonationAggregateFilter;
ChallengeBidAggregateFilter = _1ToManyDonationAggregateFilter;
ChallengeAggregateFilter = _1ToManyBidsAggregateFilter;
ChoiceAggregateFilter = Q(option__bids__donation__transactionstate='COMPLETED');
ChoiceOptionAggregateFilter = _1ToManyBidsAggregateFilter;
DonorAggregateFilter = _1ToManyDonationAggregateFilter;
EventAggregateFilter = _1ToManyDonationAggregateFilter;
  
ModelAnnotations = {
  'challenge'    : { 'amount': Sum('bids__amount', only=ChallengeAggregateFilter), 'count': Count('bids', only=ChallengeAggregateFilter) },
  'choice'       : { 'amount': Sum('option__bids__amount', only=ChoiceAggregateFilter), 'count': Count('option__bids', only=ChoiceAggregateFilter) },
  'choiceoption' : { 'amount': Sum('bids__amount', only=ChoiceOptionAggregateFilter), 'count': Count('bids', only=ChoiceOptionAggregateFilter) },
  'donor'        : { 'amount': Sum('donation__amount', only=DonorAggregateFilter), 'count': Count('donation', only=DonorAggregateFilter), 'max': Max('donation__amount', only=DonorAggregateFilter), 'avg': Avg('donation__amount', only=DonorAggregateFilter) },
  'event'        : { 'amount': Sum('donation__amount', only=EventAggregateFilter), 'count': Count('donation', only=EventAggregateFilter), 'max': Max('donation__amount', only=EventAggregateFilter), 'avg': Avg('donation__amount', only=EventAggregateFilter) },
}