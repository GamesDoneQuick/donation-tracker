from django.db.models import Count,Sum,Max,Avg,Q;
from tracker.models import *;
from datetime import *;
import pytz;

_ModelMap = {
  'challenge'     : Challenge,
  'challengebid'  : ChallengeBid,
  'choice'        : Choice,
  'choicebid'     : ChoiceBid,
  'choiceoption'  : ChoiceOption,
  'donation'      : Donation,
  'donor'         : Donor,
  'event'         : Event,
  'prize'         : Prize,
  'prizecategory' : PrizeCategory,
  'run'           : SpeedRun,
};

_GeneralFields = {
  'challenge'     : [ 'speedrun', 'name', 'description' ],
  'challengebid'  : [ 'challenge', 'donation' ],
  'choice'        : [ 'speedrun', 'name', 'description' ],
  'choicebid'     : [ 'option', 'donation' ],
  'choiceoption'  : [ 'choice', 'name' ],
  'donation'      : [ 'donor', 'comment', 'modcomment' ],
  'donor'         : [ 'email', 'alias', 'firstname', 'lastname', 'paypalemail' ],
  'event'         : [ 'short', 'name' ],
  'prize'         : [ 'name', 'description', 'winner', 'contributors' ],
  'prizecategory' : [ 'name', ],
  'run'           : [ 'name', 'description', 'runners' ],
};

_SpecificFields = {
  'challenge': {
    'event'       : 'speedrun__event',
    'eventshort'  : 'speedrun__event__short__iexact',
    'eventname'   : 'speedrun__event__name__icontains',
    'run'         : 'speedrun',
    'runname'     : 'speedrun__name__icontains',
    'name'        : 'name__icontains',
    'description' : 'description__icontains',
    'state'       : 'state__iexact',
  },
  'challengebid': {
    'event'         : 'donation__event',
    'eventshort'    : 'donation__event__short__iexact',
    'eventname'     : 'donation__event__name__icontains',
    'run'           : 'challenge__speedrun',
    'runname'       : 'challenge__speedrun__name__icontains',
    'challenge'     : 'challenge',
    'challengename' : 'challenge__name__icontains',
    'donation'      : 'donation',
    'donor'         : 'donation__donor',
    'amount'        : 'amount',
    'amount_lte'    : 'amount__lte',
    'amount_gte'    : 'amount__gte'
  },
  'choice': {
    'event'      : 'speedrun__event',
    'eventshort'  : 'speedrun__event__short__iexact',
    'eventname'   : 'speedrun__event__name__icontains',
    'run'        : 'speedrun',
    'runname'    : 'speedrun__name__icontains',
    'name'       : 'name__icontains',
    'state'      : 'state__iexact',
  },
  'choiceoption': {
    'event'      : 'choice__speedrun__event',
    'eventshort' : 'choice__speedrun__event__short__iexact',
    'eventname'  : 'choice__speedrun__event__name__icontains',
    'run'        : 'choice__speedrun',
    'runname'    : 'choice__speedrun__name__icontains',
    'choice'     : 'choice',
    'choicename' : 'choice__name__icontains',
    'name'       : 'name__icontains'
  },
  'choicebid': {
    'event'      : 'donation__event',
    'eventshort'    : 'donation__event__short__iexact',
    'eventname'     : 'donation__event__name__icontains',
    'run'        : 'option__choice__speedrun',
    'runname'    : 'option__choice__speedrun__name__icontains',
    'choice'     : 'option__choice',
    'choicename' : 'option__choice__name__icontains',
    'option'     : 'option',
    'optionname' : 'option__name__icontains',
    'donation'   : 'donation',
    'donor'      : 'donation__donor',
    'amount'     : 'amount',
    'amount_lte' : 'amount__lte',
    'amount_gte' : 'amount__gte'
  },
  'donation': {
    'event'        : 'event',
    'eventshort'   : 'event__short__iexact',
    'eventname'    : 'event__name__icontains',
    'donor'        : 'donor',
    'domain'       : 'domain',
    'transactionstate' : 'transactionstate',
    'bidstate'     : 'bidstate',
    'commentstate' : 'commentstate',
    'readstate'    : 'readstate',
    'amount'       : 'amount',
    'amount_lte'   : 'amount__lte',
    'amount_gte'   : 'amount__gte',
    'time_lte'     : 'timereceived__lte',
    'time_gte'     : 'timereceived__gte',
    'comment'      : 'comment__icontains',
    'modcomment'   : 'modcomment__icontains',
    'testdonation' : 'testdonation',
  },
  'donor': {
    'event'      : 'donation__event',
    'eventshort' : 'donation__event__short__iexact',
    'eventname'  : 'donation__event__name__icontains',
    'firstname'  : 'firstname__icontains',
    'lastname'   : 'lastname__icontains',
    'alias'      : 'alias__icontains',
    'email'      : 'email__icontains',
  },
  'event': {
    'name'        : 'name__icontains',
    'short'       : 'short__iexact',
  },
  'prize': {
    'event'                : 'event',
    'eventname'            : 'event__name__icontains',
    'eventshort'           : 'event__short__iexact',
    'category'             : 'category',
    'categoryname'         : 'category__name__icontains',
    'name'                 : 'name__icontains',
    'startrun'             : 'startrun',
    'endrun'               : 'endrun',
    'starttime_lte'        : 'starttime__lte',
    'endtime_lte'          : 'endtime__lte',
    'description'          : 'description__icontains',
    'winner'               : 'winner',
    'contributor'          : 'contributors',
    'contributorname'      : 'contributors__alias__icontains',
    'emailsent'            : 'emailsent',
  },
  'prizecategory': {
    'name'        : 'name__icontains',
  },
  'run': {
    'event'          : 'event',
    'eventname'      : 'event__name__icontains',
    'eventshort'     : 'event__short__iexact',
    'name'           : 'name__icontains',
    'runner'         : 'runners',
    'runnername'     : 'runners__alias__icontains',
    'description'    : 'description__icontains',
  },
};

_RelatedEntities = {
  'challenge'    : [ 'speedrun' ],
  'choice'       : [ 'speedrun' ],
  'choiceoption' : [ 'choice', 'choice__speedrun' ],
  'donation'     : [ 'donor' ],
  'prize'        : [ 'category', 'startrun', 'endrun', 'winner' ],
};

_DeferredFields = {
  'challenge'    : [ 'speedrun__description', 'speedrun__endtime', 'speedrun__starttime', 'speedrun__runners', 'speedrun__sortkey', ],
  'choice'       : [ 'speedrun__description', 'speedrun__endtime', 'speedrun__starttime', 'speedrun__runners', 'speedrun__sortkey', ],
  'choiceoption' : [ 'choice__speedrun__description', 'choice__speedrun__endtime', 'choice__speedrun__starttime', 'choice__speedrun__runners', 'choice__speedrun__sortkey', 'choice__description', 'choice__pin', 'choice__state', ],
}

_Annotations = {
  'challenge'    : { 'total': Sum('bids__amount'), 'bidcount': Count('bids') },
  'choice'       : { 'total': Sum('option__bids__amount'), 'bidcount': Count('option__bids') },
  'choiceoption' : { 'total': Sum('bids__amount'), 'bidcount': Count('bids') },
  'donor'        : { 'total': Sum('donation__amount'), 'count': Count('donation'), 'max': Max('donation__amount'), 'avg': Avg('donation__amount') },
  'event'        : { 'total': Sum('donation__amount'), 'count': Count('donation'), 'max': Max('donation__amount'), 'avg': Avg('donation__amount') },
}

_FKMap = {
  'winner': 'donor', 
  'speedrun': 'run',
  'startrun': 'run', 
  'endrun': 'run',
  'option': 'choiceoption',
  'category': 'prizecategory', 
  'runners': 'donor', 
  'contributors': 'donor' 
};

_DonorEmailFields = ['email', 'paypalemail'];
_DonorNameFields = ['firstname', 'lastname'];
_SpecialMarkers = ['icontains', 'contains', 'iexact', 'exact', 'lte', 'gte'];

# additional considerations for permission related visibility at the 'field' level
def add_permissions_checks(rootmodel, key, query, user=None):
  toks = key.split('__');
  leading = '';
  if len(toks) >= 2:
    tail = toks[-2];
    ftail = _FKMap.get(tail,tail);
    rootmodel = ftail;
    leading = '__'.join(toks[:-1]) + '__';
  field = toks[-1];
  if rootmodel == 'donor':
    visField = leading + 'visibility';
    if (field in _DonorEmailFields) and (user == None or not user.has_perm('view_emails')):
      # Here, we just want to remove the query altogether, since there is no circumstance that we want personal contact emails displayed publicly without permissions
      query = Q();
    elif (field in _DonorNameFields) and (user == None or not user.has_perm('view_usernames')):
      query &= Q(**{ visField: 'FULL' });
    elif (field == 'alias') and (user == None or not user.has_perm('view_usernames')):
      query &= Q(Q(**{ visField: 'FULL' }) | Q(**{ visField: 'ALIAS' }));
  elif rootmodel == 'donation':
    if (field == 'testdonation') and (user == None or not user.has_perm('view_test')):
      query = Q();
    if (field == 'comment') and (user == None or not user.has_perm('view_comments')):
      # only allow searching the textual content of approved comments
      commentStateField = leading + 'commentstate';
      query &= Q(**{ commentStateField: 'APPROVED' });
  elif rootmodel == 'choice' or rootmodel == 'challenge':
    # Prevent 'hidden' bids from showing up in public queries
    if (field == 'state') and (user == None or not user.has_perm('view_hidden')):
      query &= ~Q(**{ key: 'HIDDEN' });
  return query;

def text_filter(fields, searchString):
  query = Q();
  if searchString:
    for field in fields:
      query |= Q(**{field + "__icontains": searchString});
  return query;

def recurse_keys(key):
  tail = key.split('__')[-1];
  ftail = _FKMap.get(tail,tail);
  if ftail in _GeneralFields:
    ret = [];
    for key in _GeneralFields[ftail]:
      for k in recurse_keys(key):
        ret.append(tail + '__' + k);
    return ret;
  return [key];
  
def build_general_query_piece(rootmodel, key, text, user=None):
  resultQuery = Q(**{ key + '__icontains': text });
  resultQuery = add_permissions_checks(rootmodel, key, resultQuery, user=user);
  return resultQuery;

# This creates a 'q'-esque Q-filter, similar to the search model of the django admin
def model_general_filter(model, text, user=None):
  fields = set()
  for key in _GeneralFields[model]:
    fields |= set(recurse_keys(key))
  fields = list(fields);
  query = Q();
  for field in fields:
    query |= build_general_query_piece(model, field, text, user=user);
  return query;
  
# This creates a more specific filter, using UA's json API as a basis
def model_specific_filter(model, searchDict, user=None):
  query = Q();
  modelSpecifics = _SpecificFields[model];
  for key in searchDict:
    if key in modelSpecifics:
      # A list/tuple of entries implies an 'or'-ing between all specified values
      # this isn't possible in the current url method, but it could be in the future if we had a way to encode lists (possibly by escaping commas in normal strings)
      values = searchDict[key];
      fieldQuery = Q();
      if isinstance(values, basestring) or not hasattr(values, '__iter__'):
        values = [values];
      for value in values: 
        fieldQuery |= Q( **{ modelSpecifics[key]: value });
      fieldQuery = add_permissions_checks(model, key, fieldQuery, user=user);
      query &= fieldQuery;
  return query;

def default_time(time):
  if time is None:
    return datetime.utcnow();
  else:
    return time;

_DEFAULT_DONATION_DELTA = timedelta(hours=3);
_DEFAULT_DONATION_MAX = 200;
_DEFAULT_DONATION_MIN = 25;

# There is a slight complication in how this works, in that we cannot use the 'limit' set-up as a general filter mechanism, so these methods return the actual result, rather than a filter object
def get_recent_donations(donations=None, minDonations=_DEFAULT_DONATION_MIN, maxDonations=_DEFAULT_DONATION_MAX, delta=_DEFAULT_DONATION_DELTA, queryOffset=None):
  offset = default_time(queryOffset);
  if donations == None:
    donations = Donation.objects.all();
  highFilter = donations.filter(timereceived__gte=offset-delta);
  count = highFilter.count();
  if count > maxDonations:
    donations = donations[:maxDonations];
  elif count < minDonations:
    donations = donations[:minDonations];
  else:
    donations = highFilter;
  return donations;

_DEFAULT_RUN_DELTA = timedelta(hours=3);
_DEFAULT_RUN_MAX = 7;
_DEFAULT_RUN_MIN = 3;

def get_upcomming_runs(runs=None, includeCurrent=True, maxRuns=_DEFAULT_RUN_MAX, minRuns=_DEFAULT_RUN_MIN, delta=_DEFAULT_RUN_DELTA, queryOffset=None):
  offset = default_time(queryOffset);
  if runs == None:
    runs = SpeedRun.objects.all();
  if includeCurrent:
    runs = runs.filter(endtime__gte=offset);
  else:
    runs = runs.filter(starttime__gte=offset);
  highFilter = runs.filter(endtime__lte=offset+delta);
  count = highFilter.count();
  if count > maxRuns:
    runs = runs[:maxRuns];
  elif count < minRuns:
    runs = runs[:minRuns];
  else:
    runs = highFilter;
  return runs;

def get_future_runs(**kwargs):
  return get_upcomming_runs(includeCurrent=False, **kwargs);

def upcomming_bid_filter(**kwargs):
  runs = get_upcomming_runs(**kwargs);
  runIds = list(map(lambda x: x.id, runs));
  return Q(speedrun__in=runIds);
  
def future_bid_filter(**kwargs):
  return upcomming_bid_filter(includeCurrent=False, **kwargs);

# Gets all of the current prizes that are possible right now (and also _sepcific_ to right now)
def concurrent_prizes_filter(runs):
  if runs.count() == 0:
    return Prize.objects.none();
  startTime = runs[0].starttime;
  endTime = runs[-1].endtime;
  # yes, the filter query here is correct.  We want to get all prizes unwon prizes that _start_ before the last run in the list _ends_, and likewise all prizes that _end_ after the first run in the list _starts_.
  return Q(winner=None) & (Q(speedrun__starttime__gte=endTime, speedrun__endtime__lte=startTime) | Q(starttime__gte=endTime, endtime__lte=startTime));
  
def current_prizes_filter(queryTime=None):
  offset = default_time(queryOffset);
  runs = SpeedRun.objects.filter(starttime__lte=offset, endtime__gte=offset);
  return concurrent_prizes_filter(runs);
  
def upcomming_prizes_filter(**kwargs):
  runs = get_upcomming_runs(**kwargs);
  return concurrent_prizes_filter(runs);
  
def future_prizes_filter(**kwargs):
  return upcomming_prizes_filter(includeCurrent=False);
  
def run_model_query(model, params, user=None):
  if model == 'speedrun':
    model = 'run'; # we should really just rename all instances of it already!
  filtered = _ModelMap[model].objects.all();
  if 'id' in params:
    filtered = filtered.filter(id=params['id']);
  if 'q' in params:
    filtered = filtered.filter(model_general_filter(model, params['q'], user=user));
  filtered = filtered.filter(model_specific_filter(model, params, user=user));
  if model == 'donation' and 'filter' in params:
    filter = params['filter'];
    if filter == 'recent':
      filtered = get_recent_donations(filtered);
    # TODO: add a special parameter from the views to always show confirmed donations only, or a special parameter to show all donations, but only if they have the right permissions
  elif model == 'choice' or model == 'challenge' and 'filter' in params:
    filter = params['filter'];
    if filter == 'open':
      filtered = filtered.filter(state='OPENED');
    elif filter == 'closed':
      filtered = filtered.filter(state='CLOSED');
    elif filter == 'current':
      filtered = filtered.filter(upcomming_bid_filter());
    elif filter == 'future':
      filtered = filtered.filter(future_bid_filter());
  elif model == 'run' and 'filter' in params:
    filter = params['filter'];
    if filter == 'current':
      filtered = get_upcomming_runs(runs=filtered);
    elif filter == 'future':
      filtered = get_future_runs(runs=filtered);
  elif model == 'prize' and 'filter' in params:
    filter = params['filter'];
    if filter == 'current':
      filtered = filtered.filter(concurrent_prizes_filter(),winner=None);
    elif filter == 'upcomming':
      filtered = filtered.filter(upcomming_prizes_filter(),winner=None);
    elif filter == 'won':
      filtered = filtered.filter(~Q(winner=None));
    elif filter == 'unwon':
      filtered = filtered.filter(winner=None);
  return filtered;
  
_RUN_FILTER_FIELDS = ['name', 'runners__alias', 'description'];
def run_text_filter(searchString): 
  return text_filter(_RUN_FILTER_FIELDS, searchString);

_BID_FILTER_FIELDS = ['name', 'description', 'speedrun__name']; 
def bid_text_filter(searchString):
  return text_filter(_BID_FILTER_FIELDS, searchString);

_PRIZE_FILTER_FIELDS = ['name', 'description', 'provided', 'startrun__name', 'endrun__name']
def prize_text_filter(searchString):
  return text_filter(_PRIZE_FILTER_FIELDS, searchString);

_DEFAULT_RUN_DELTA = timedelta(hours=3);
_DEFAULT_RUN_MAX = 7;
_DEFAULT_RUN_MIN = 3;
_DEFAULT_DONATION_DELTA = timedelta(hours=3);
_DEFAULT_DONATION_MAX = 200;
_DEFAULT_DONATION_MIN = 25;

class EventFilter:
  def __init__(self, event, runDelta=_DEFAULT_RUN_DELTA, runMin=_DEFAULT_RUN_MIN, runMax=_DEFAULT_RUN_MAX, donationDelta=_DEFAULT_DONATION_DELTA, donationMin=_DEFAULT_DONATION_MIN, donationMax=_DEFAULT_DONATION_MAX, queryOffset=None):
    self.runDelta = runDelta;
    self.runMin = runMin;
    self.runMax = runMax;
    self.donationDelta = donationDelta;
    self.donationMin = donationMin;
    self.donationMax = donationMax;
    self.queryOffset = queryOffset;

    if event.id:
      self.event = event;
    else:
      self.event = None;

    self.all_bids_q = Q();
    if self.event:
      self.all_bids_q &= Q(speedrun__event=self.event);

    self.all_donations_q = Q(amount__gt=Decimal('0.00'));
    if self.event:
      self.all_donations_q &= Q(event=self.event,testdonation=event.usepaypalsandbox); 
    else:
      self.all_donations_q &= Q(testdonation=False);
      
    self.all_donors_q = Q();
    if self.event:
      self.all_donors_q &= Q(donation__event=self.event);

    self.all_runs_q = Q();
    if self.event:
      self.all_runs_q &= Q(event=self.event);

    self.all_prizes_q = Q();
    if self.event:
      self.all_prizes_q &= Q(event=self.event);

  def get_offset(self):
    if self.queryOffset is None:
      return datetime.utcnow();
    else:
      return self.queryOffset;

  def all_donors(self):
    return Donor.objects.filter(self.all_donors_q).distinct();

  def all_donations(self):
    return Donation.objects.filter(self.all_donations_q);

  def valid_donations(self):
    return self.all_donations().filter(transactionstate='COMPLETED');

  def recent_donations(self):
    donations = self.valid_donations().reverse();
    donations = donations[:self.donationMax];
    count = donations.count();
    if count > self.donationMin:
      donations = self.valid_donations().filter(timereceived__gte=self.get_offset()-self.donationDelta)[:self.donationMax];
    return donations;
      
  def all_runs(self, searchString=None):
    runs = SpeedRun.objects.filter(self.all_runs_q, run_text_filter(searchString));
    return runs;

  def upcomming_runs(self, includeCurrent=False, **kwargs):
    runs = self.all_runs(**kwargs);
    offset = self.get_offset();
    if includeCurrent:
      runs = runs.filter(endtime__gte=offset);
    else:
      runs = runs.filter(starttime__gte=offset);
    highFilter = runs.filter(endtime__lte=offset+self.runDelta);
    count = highFilter.count();
    if count > self.runMax:
      runs = runs[:self.runMax];
    elif count < self.runMin:
      runs = runs[:self.runMin];
    else:
      runs = highFilter;
    return runs;

  def all_choices(self, searchString=None):
    return Choice.objects.filter(self.all_bids_q, bid_text_filter(searchString));
 
  def visible_choices(self, **kwargs):
    return self.all_choices(**kwargs).exclude(state='HIDDEN');

  def open_choices(self, **kwargs):
    return self.all_choices(**kwargs).filter(state='OPENED');

  def closed_choices(self, **kwargs):
    return self.all_choices(**kwargs).filter(state='CLOSED');

  def upcomming_choices(self, includeCurrent=False, **kwargs):
    runs = self.upcomming_runs(includeCurrent=includeCurrent);
    runIds = list(map(lambda x: x.id, runs));
    return self.open_choices(**kwargs).filter(speedrun__in=runIds);

  def all_challenges(self, searchString=None):
    return Challenge.objects.filter(self.all_bids_q, bid_text_filter(searchString));

  def visible_challenges(self, **kwargs):
    return self.all_challenges(**kwargs).exclude(state='HIDDEN');

  def open_challenges(self, **kwargs):
    return self.all_challenges(**kwargs).filter(state='OPENED');

  def closed_challenges(self, **kwargs):
    return self.all_challenges(**kwargs).filter(state='CLOSED');

  def upcomming_challenges(self, includeCurrent=False, **kwargs):
    runs = self.upcomming_runs(includeCurrent=includeCurrent);
    runIds = list(map(lambda x: x.id, runs));
    return self.open_challenges(**kwargs).filter(speedrun__in=runIds);

  def all_prizes(self, searchString=None, category=None):
    prizes = Prize.objects.filter(self.all_prizes_q, prize_text_filter(searchString));
    if category:
      prizes = prizes.filter(category=category);
    return prizes;

  def won_prizes(self, **kwargs):
    return self.all_prizes(**kwargs).exclude(winner=None);

  def unwon_prizes(self, **kwargs):
    return self.all_prizes(**kwargs).filter(winner=None);

  def upcomming_prizes(self, includeCurrent=False, **kwargs):
    runs = self.upcomming_runs(includeCurrent=includeCurrent);
    if runs.count() == 0:
      return Prize.objects.none();
    startTime = runs[0].starttime;
    endTime = runs[-1].endtime;
    # yes, the filter query here is correct.  We want to get all prizes that _start_ before the last run in the list _ends_, and likewise all prizes that _end_ after the first run in the list _starts_.
    return unwon_prizes(self, **kwargs).filter(Q(speedrun__starttime__gte=endTime, speedrun__endtime__lte=startTime) | Q(starttime__gte=endTime, endtime__lte=startTime));
 