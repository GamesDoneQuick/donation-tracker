from django.db.models import Count,Sum,Max,Avg,Q,F;
from tracker.models import *;
from datetime import *;
import pytz;
import viewutil;
import dateutil.parser;

# TODO: fix these to make more sense, it should in general only be querying top-level bids

_ModelMap = {
  'allbids'       : Bid,
  'bid'           : Bid,
  'bidtarget'     : Bid,
  'donationbid'   : DonationBid,
  'donation'      : Donation,
  'donor'         : Donor,
  'event'         : Event,
  'prize'         : Prize,
  'prizecategory' : PrizeCategory,
  'run'           : SpeedRun,
};

_ModelDefaultQuery = {
  'bidtarget'     : Q(options__isnull=True, istarget=True),
  'bid'           : Q(level=0),
};

_ModelReverseMap = dict([(v,k) for k,v in _ModelMap.items()])

_GeneralFields = {
  # There was a really weird bug when doing the full recursion on speedrun, where it would double-select the related bids in aggregate queries
  # it seems to be related to selecting the donor table as part of the 'runners' recurse thing
  # it only applied to challenges too for some reason.  I can't figure it out, and I don't really want to waste more time on it, so I'm just hard-coding it to do the specific speedrun fields only
  'bid'           : [ 'event', 'speedrun', 'name', 'description'],
  'allbids'       : [ 'event', 'speedrun', 'name', 'description', 'parent' ],
  'bidtarget'     : [ 'event', 'speedrun', 'name', 'description', 'parent' ],
  'donationbid'   : [ 'donation', 'bid' ],
  'donation'      : [ 'donor', 'comment', 'modcomment' ],
  'donor'         : [ 'email', 'alias', 'firstname', 'lastname', 'paypalemail' ],
  'event'         : [ 'short', 'name' ],
  'prize'         : [ 'name', 'description', 'winner', 'contributors' ],
  'prizecategory' : [ 'name', ],
  'run'           : [ 'name', 'description', 'runners' ],
};

_SpecificFields = {
  'bid': {
    'event'       : ['speedrun__event', 'event'],
    'eventshort'  : ['speedrun__event__short__iexact', 'event__short__iexact'],
    'eventname'   : ['speedrun__event__name__icontains', 'event__name__icontains'], 
    'run'         : 'speedrun',
    'runname'     : 'speedrun__name__icontains',
    'name'        : 'name__icontains',
    'description' : 'description__icontains',
    'state'       : 'state__iexact',
  },
  'allbids' : {
    'event'       : ['speedrun__event', 'event'],
    'eventshort'  : ['speedrun__event__short__iexact', 'event__short__iexact'],
    'eventname'   : ['speedrun__event__name__icontains', 'event__name__icontains'], 
    'run'         : 'speedrun',
    'runname'     : 'speedrun__name__icontains',
    'name'        : 'name__icontains',
    'description' : 'description__icontains',
    'state'       : 'state__iexact',
  },
  'bidtarget': { #TODO: remove redundancy between these 2, or change the filter logic to be smarter (sub-model maybe?)
    'event'       : ['speedrun__event', 'event'],
    'eventshort'  : ['speedrun__event__short__iexact', 'event__short__iexact'],
    'eventname'   : ['speedrun__event__name__icontains', 'event__name__icontains'], 
    'run'         : 'speedrun',
    'runname'     : 'speedrun__name__icontains',
    'parent'      : 'parent',
    'parentname'  : 'parent__name__icontains',
    'name'        : 'name__icontains',
    'description' : 'description__icontains',
    'state'       : 'state__iexact',
  },
  'donationbid': {
    'event'         : 'donation__event',
    'eventshort'    : 'donation__event__short__iexact',
    'eventname'     : 'donation__event__name__icontains',
    'run'           : 'bid__speedrun',
    'runname'       : 'bid__speedrun__name__icontains',
    'bid'           : 'bid',
    'bidname'       : 'bid__name__icontains',
    'donation'      : 'donation',
    'donor'         : 'donation__donor',
    'amount'        : 'amount',
    'amount_lte'    : 'amount__lte',
    'amount_gte'    : 'amount__gte'
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
    'visibility' : 'visibility__iexact',
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

_FKMap = {
  'winner': 'donor', 
  'speedrun': 'run',
  'startrun': 'run', 
  'endrun': 'run',
  'option': 'bid',
  'category': 'prizecategory', 
  'runners': 'donor', 
  'contributors': 'donor', 
  'parent': 'bid', 
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
  elif rootmodel == 'bid':
    # Prevent 'hidden' bids from showing up in public queries
    if (field == 'state') and (user == None or not user.has_perm('view_hidden')):
      query &= ~Q(**{ key: 'HIDDEN' });
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
  if text:
    resultQuery = Q(**{ key + '__icontains': text });
    resultQuery = add_permissions_checks(rootmodel, key, resultQuery, user=user);
  else:
    resultQuery = Q();
  return resultQuery;

def normalize_model_param(model):
  if model == 'speedrun':
    model = 'run'; # we should really just rename all instances of it already!
  if model not in _ModelMap:
    model = _ModelReverseMap[model];
  return model

# This creates a 'q'-esque Q-filter, similar to the search model of the django admin
def model_general_filter(model, text, user=None):
  fields = set()
  model = normalize_model_param(model);
  for key in _GeneralFields[model]:
    fields |= set(recurse_keys(key))
  fields = list(fields);
  query = Q();
  for field in fields:
    query |= build_general_query_piece(model, field, text, user=user);
  return query;
  
# This creates a more specific filter, using UA's json API implementation as a basis
def model_specific_filter(model, searchDict, user=None):
  query = Q();
  model = normalize_model_param(model);
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
        # allows modelspecific to be a single key, or multiple values 
        modelSpecific = modelSpecifics[key];
        if isinstance(modelSpecific, basestring):
          modelSpecific = [modelSpecific];
        for searchKey in modelSpecific:
          fieldQuery |= Q( **{ searchKey: value });
      fieldQuery = add_permissions_checks(model, key, fieldQuery, user=user);
      query &= fieldQuery;
  return query;

def canonicalBool(b):
  if isinstance(b, basestring):
    if b.lower() in ['t', 'True', 'true', 'y', 'yes']:
      b = True;
    elif b.lower() in ['f', 'False', 'false', 'n', 'no']:
      b = False;
    else:
      b = None;
  return b;
  
def default_time(time):
  if time is None:
    time = datetime.utcnow();
  elif isinstance(time, basestring):
    time = dateutil.parser.parse(time);
  return time.replace(tzinfo=pytz.utc);

_DEFAULT_DONATION_DELTA = timedelta(hours=3);
_DEFAULT_DONATION_MAX = 200;
_DEFAULT_DONATION_MIN = 25;

# There is a slight complication in how this works, in that we cannot use the 'limit' set-up as a general filter mechanism, so these methods return the actual result, rather than a filter object
def get_recent_donations(donations=None, minDonations=_DEFAULT_DONATION_MIN, maxDonations=_DEFAULT_DONATION_MAX, delta=_DEFAULT_DONATION_DELTA, queryOffset=None):
  offset = default_time(queryOffset);
  if donations == None:
    donations = Donation.objects.all();
  if delta:
    highFilter = donations.filter(timereceived__gte=offset-delta);
  else:
    highFilter = donations;
  count = highFilter.count();
  if maxDonations != None and count > maxDonations:
    donations = donations[:maxDonations];
  elif minDonations != None and count < minDonations:
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
  if delta:
    highFilter = runs.filter(endtime__lte=offset+delta);
  else:
    highFilter = runs;
  count = highFilter.count();
  if maxRuns != None and count > maxRuns:
    runs = runs[:maxRuns];
  elif minRuns != None and count < minRuns:
    runs = runs[:minRuns];
  else:
    runs = highFilter;
  return runs;

def get_future_runs(**kwargs):
  return get_upcomming_runs(includeCurrent=False, **kwargs);

def upcomming_bid_filter(**kwargs):
  runs = get_upcomming_runs(**kwargs);
  return Q(speedrun__in=runs);
  
def future_bid_filter(**kwargs):
  return upcomming_bid_filter(includeCurrent=False, **kwargs);

def get_completed_challenges(querySet):
  return querySet.filter(state='OPENED').annotate(viewutil.ModelAnnotations['challenge']).filter(goal__isnull=False, amount__gte=F('goal'));
  
# Gets all of the current prizes that are possible right now (and also _sepcific_ to right now)
def concurrent_prizes_filter(runs):
  if runs.count() == 0:
    return Q(id=None);
  startTime = runs[0].starttime;
  endTime = runs[-1].endtime;
  # yes, the filter query here is correct.  We want to get all prizes unwon prizes that _start_ before the last run in the list _ends_, and likewise all prizes that _end_ after the first run in the list _starts_.
  return Q(winner=None) & (Q(startrun__starttime__lte=endTime, endrun__endtime__gte=startTime) | Q(starttime__lte=endTime, endtime__gte=startTime));
  
def current_prizes_filter(queryTime=None):
  offset = default_time(queryTime);
  return Q(winner=None) & (Q(startrun__starttime__lte=offset, endrun__endtime__gte=offset) | Q(starttime__lte=offset, endtime__gte=offset));
  
def upcomming_prizes_filter(**kwargs):
  runs = get_upcomming_runs(**kwargs);
  return concurrent_prizes_filter(runs);
  
def future_prizes_filter(**kwargs):
  return upcomming_prizes_filter(includeCurrent=False, **kwargs);
  
def todraw_prizes_filter(queryTime=None):
  offset = default_time(queryTime);
  return Q(winner=None) & (Q(endrun__endtime__lte=offset) | Q(endtime__lte=offset));
  
def run_model_query(model, params={}, user=None, mode='user'):
  model = normalize_model_param(model);
  
  filtered = _ModelMap[model].objects.all();
  
  if model in _ModelDefaultQuery:
    filtered = filtered.filter(_ModelDefaultQuery[model]);
  
  if 'id' in params:
    filtered = filtered.filter(id=params['id']);
  if 'q' in params:
    filtered = filtered.filter(model_general_filter(model, params['q'], user=user));
  filtered = filtered.filter(model_specific_filter(model, params, user=user));
  if mode == 'user':
    filtered = filtered.filter(user_restriction_filter(model));
  filtered = filtered.distinct();
  if 'feed' in params:
    filtered = apply_feed_filter(filtered, model, params['feed'], params, user=user);
  return filtered;

def user_restriction_filter(model):
  if model == 'bid' or model == 'bidtarget' or model == 'allbids':
    return ~Q(state='HIDDEN');
  elif model == 'donation':
    return Q(transactionstate='COMPLETED', testdonation=F('event__usepaypalsandbox'));
  elif model == 'donor':
    return Q(donation__testdonation=F('donation__event__usepaypalsandbox')); 
  else:
    return Q();

def apply_feed_filter(query, model, feedName, params, user=None, noslice=False):
  if 'noslice' in params:
    noslice = canonicalBool(params['noslice']);
  if model == 'donation':
    if feedName == 'recent':
      callParams = { 'donations': query };
      if 'delta' in params:
        callParams['delta']  = timedelta(minutes=int(params['delta']));
      if 'offset' in params:
        callParams['queryOffset'] = default_time(params['offset']);
      if 'maxDonations' in params:
        callParams['maxDonations'] = int(params['maxDonations']);
      if 'minDonations' in params:
        callParams['minDonations'] = int(params['minDonations']);
      if noslice:
        callParams['maxDonations'] = None;
        callParams['minDonations'] = None;
      query = get_recent_donations(**callParams);
  elif model in ['bid', 'bidtarget', 'allbids']:
    if feedName == 'open':
      query = query.filter(state='OPENED');
    elif feedName == 'closed':
      query = query.filter(state='CLOSED');
    elif feedName == 'current':
      callParams = {};
      if 'maxRuns' in params:
        callParams['maxRuns'] = int(params['maxRuns']);
      if 'minRuns' in params:
        callParams['minRuns'] = int(params['minRuns']);
      if noslice:
        callParams['maxRuns'] = None;
        callParams['minRuns'] = None;
      if 'offset' in params:
        callParams['queryOffset'] = default_time(params['offset']);
      query = query.filter(upcomming_bid_filter(**callParams));
    elif feedName == 'future':
      callParams = {};
      if 'maxRuns' in params:
        callParams['maxRuns'] = int(params['maxRuns']);
      if 'minRuns' in params:
        callParams['minRuns'] = int(params['minRuns']);
      if noslice:
        callParams['maxRuns'] = None;
        callParams['minRuns'] = None;
      if 'delta' in params:
        callParams['delta'] = timedelta(minutes=int(toks[1]));
      if 'offset' in params:
        callParams['queryOffset'] = default_time(params['offset']);
      query = query.filter(future_bid_filter(**callParams));
    elif feedName == 'completed':
      query = get_completed_challenges(query);
  elif model == 'run':
    callParams = { 'runs': query };
    if feedName == 'current':
      if 'maxRuns' in params:
        callParams['maxRuns'] = int(params['maxRuns']);
      if 'minRuns' in params:
        callParams['minRuns'] = int(params['minRuns']); 
      if noslice:
        callParams['maxRuns'] = None;
        callParams['minRuns'] = None;
      if 'offset' in params:
        callParams['queryOffset'] = default_time(params['offset']);
      query = get_upcomming_runs(**callParams);
    elif feedName == 'future':
      if 'maxRuns' in params:
        callParams['maxRuns'] = int(params['maxRuns']);
      if 'minRuns' in params:
        callParams['minRuns'] = int(params['minRuns']);
      if noslice:
        callParams['maxRuns'] = None;
        callParams['minRuns'] = None;
      if 'delta' in params:
        callParams['delta'] = timedelta(minutes=int(toks[1]));
      if 'offset' in params:
        callParams['queryOffset'] = default_time(params['offset']);
      query = get_future_runs(**callParams);
  elif model == 'prize':
    if feedName == 'current':
      callParams = {};
      if 'maxRuns' in params:
        callParams['maxRuns'] = int(params['maxRuns']);
      if 'minRuns' in params:
        callParams['minRuns'] = int(params['minRuns']);
      if noslice:
        callParams['maxRuns'] = None;
        callParams['minRuns'] = None;
      if 'offset' in params:
        callParams['queryOffset'] = default_time(params['offset']);
      query = query.filter(current_prizes_filter(**callParams));
    elif feedName == 'upcomming':
      callParams = {};
      if 'maxRuns' in params:
        callParams['maxRuns'] = int(params['maxRuns']);
      if 'minRuns' in params:
        callParams['minRuns'] = int(params['minRuns']);
      if noslice:
        callParams['maxRuns'] = None;
        callParams['minRuns'] = None;
      if 'delta' in params:
        callParams['delta'] = timedelta(minutes=int(toks[1]));
      if 'offset' in params:
        callParams['queryOffset'] = default_time(params['offset']);
      x = upcomming_prizes_filter(**callParams);
      query = query.filter(x);
    elif feedName == 'won':
      query = query.filter(~Q(winner=None));
    elif feedName == 'unwon':
      query = query.filter(winner=None);
    elif feedName == 'todraw':
      query = query.filter(todraw_prizes_filter());
  return query;
