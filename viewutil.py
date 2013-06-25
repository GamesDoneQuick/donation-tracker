import re;
from tracker.models import *;
import filters;
from django.db.models import Count,Sum,Max,Avg,Q
import simplejson;
import random;

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

# Parses a 'natural language' list, i.e. seperated by commas, semi-colons, and 'and's
def natural_list_parse(s):
  result = [];
  tokens = [s];
  seperators = [',',';','&','+',' and ',' or ', ' and/or ']
  for sep in seperators:
    newtokens = [];
    for token in tokens:
      while len(token) > 0:
        before, found, after = token.partition(sep);
        newtokens.append(before);
        token = after;
    tokens = newtokens;
  return list(filter(lambda x: len(x) > 0, map(lambda x: x.strip(), tokens)));

def draw_prize(prize):
  eligible = prize.eligibledonors();
  key = hash(simplejson.dumps(eligible,use_decimal=True));
  if not eligible:
    return False, "Prize: " + prize.name + " has no eligible donors";
  else:
    rand = random.Random(key);
    psum = reduce(lambda a,b: a+b['weight'], eligible, 0.0);
    result = rand.random() * psum;
    ret = {'sum': psum, 'result': result}
    for d in eligible:
      if result < d['weight']:
        try:
          prize.winner = Donor.objects.get(pk=d['donor']);
          prize.emailsent = False;
        except Exception as e:
          return False, "Error drawing prize: " + prize.name + ", " + str(e);
      result -= d['weight'];
    prize.save();
    return True, "Prize Drawn Successfully";
  
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
