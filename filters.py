from django.db.models import Count,Sum,Max,Avg,Q,F
from tracker.models import *
from datetime import *
import pytz
import viewutil
import dateutil.parser

# TODO: fix these to make more sense, it should in general only be querying top-level bids

_ModelMap = {
  'allbids'       : Bid,
  'bid'           : Bid,
  'bidtarget'     : Bid,
  'bidsuggestion' : BidSuggestion,
  'donationbid'   : DonationBid,
  'donation'      : Donation,
  'donor'         : Donor,
  'donorcache'    : DonorCache,
  'event'         : Event,
  'prize'         : Prize,
  'prizeticket'   : PrizeTicket,
  'prizecategory' : PrizeCategory,
  'prizewinner'   : PrizeWinner,
  'prizeentry'    : DonorPrizeEntry,
  'run'           : SpeedRun,
  'log'           : Log,
  'runner'        : Runner,
}

_ModelDefaultQuery = {
  'bidtarget'     : Q(allowuseroptions=True) | Q(options__isnull=True, istarget=True),
  'bid'           : Q(level=0),
}

_ModelReverseMap = dict([(v,k) for k,v in _ModelMap.items()])

_GeneralFields = {
  # There was a really weird bug when doing the full recursion on speedrun, where it would double-select the related bids in aggregate queries
  # it seems to be related to selecting the donor table as part of the 'runners' recurse thing
  # it only applied to challenges too for some reason.  I can't figure it out, and I don't really want to waste more time on it, so I'm just hard-coding it to do the specific speedrun fields only
  'bid'           : [ 'event', 'speedrun', 'name', 'description', 'shortdescription'],
  'allbids'       : [ 'event', 'speedrun', 'name', 'description', 'shortdescription', 'parent' ],
  'bidtarget'     : [ 'event', 'speedrun', 'name', 'description', 'shortdescription', 'parent' ],
  'bidsuggestion' : [ 'name', 'bid' ],
  'donationbid'   : [ 'donation', 'bid' ],
  'donation'      : [ 'donor', 'comment', 'modcomment' ],
  'donor'         : [ 'email', 'alias', 'firstname', 'lastname', 'paypalemail' ],
  'event'         : [ 'short', 'name' ],
  'prize'         : [ 'name', 'description', 'shortdescription', 'prizewinner' ],
  'prizeticket'   : [ 'prize', 'donation', ],
  'prizecategory' : [ 'name', ],
  'prizewinner'   : [ 'prize', 'winner' ],
  'prizeentry'    : [ 'prize', 'donor' ],
  'run'           : [ 'name', 'description', 'runners' ],
  'log'           : [ 'category', 'message', 'event' ],
  'runner'        : [ 'name', 'stream', 'twitter', 'youtube', ],
}

_SpecificFields = {
  'bid': {
    'event'       : ['speedrun__event', 'event'],
    'eventshort'  : ['speedrun__event__short__iexact', 'event__short__iexact'],
    'eventname'   : ['speedrun__event__name__icontains', 'event__name__icontains'], 
    'locked'      : 'event__locked',
    'run'         : 'speedrun',
    'runname'     : 'speedrun__name__icontains',
    'name'        : 'name__icontains',
    'description' : 'description__icontains',
    'shortdescription': 'shortdescription__icontains',
    'state'       : 'state__iexact',
    'revealedtime_gte' : 'revealedtime__gte',
    'revealedtime_lte' : 'revealedtime__lte',
    'istarget'    : 'istarget',
    'allowuseroptions' : 'allowuseroptions',
    'total_gte'   : 'total__gte',
    'total_lte'   : 'total__lte',
    'count_gte'   : 'count__gte',
    'count_lte'   : 'count__lte',
    'count'       : 'count',
  },
  'allbids' : {
    'event'       : ['speedrun__event', 'event'],
    'eventshort'  : ['speedrun__event__short__iexact', 'event__short__iexact'],
    'eventname'   : ['speedrun__event__name__icontains', 'event__name__icontains'], 
    'locked'      : 'event__locked',
    'run'         : 'speedrun',
    'runname'     : 'speedrun__name__icontains',
    'name'        : 'name__icontains',
    'description' : 'description__icontains',
    'shortdescription': 'shortdescription__icontains',
    'state'       : 'state__iexact',
    'revealedtime_gte' : 'revealedtime__gte',
    'revealedtime_lte' : 'revealedtime__lte',
    'istarget'    : 'istarget',
    'allowuseroptions' : 'allowuseroptions',
    'total_gte'   : 'total__gte',
    'total_lte'   : 'total__lte',
    'count_gte'   : 'count__gte',
    'count_lte'   : 'count__lte',
    'count'       : 'count',
  },
  'bidtarget': { #TODO: remove redundancy between these 2, or change the filter logic to be smarter (sub-model maybe?)
    'event'       : ['speedrun__event', 'event'],
    'eventshort'  : ['speedrun__event__short__iexact', 'event__short__iexact'],
    'eventname'   : ['speedrun__event__name__icontains', 'event__name__icontains'], 
    'locked'      : 'event__locked',
    'run'         : 'speedrun',
    'runname'     : 'speedrun__name__icontains',
    'parent'      : 'parent',
    'parentname'  : 'parent__name__icontains',
    'name'        : 'name__icontains',
    'description' : 'description__icontains',
    'shortdescription': 'shortdescription__icontains',
    'state'       : 'state__iexact',
    'revealedtime_gte' : 'revealedtime__gte',
    'revealedtime_lte' : 'revealedtime__lte',
    'istarget'    : 'istarget',
    'allowuseroptions' : 'allowuseroptions',
    'total_gte'   : 'total__gte',
    'total_lte'   : 'total__lte',
    'count_gte'   : 'count__gte',
    'count_lte'   : 'count__lte',
    'count'       : 'count',
  },
  'bidsuggestion': {
    'event'       : ['bid__speedrun__event', 'bid__event'],
    'eventshort'  : ['bid__speedrun__event__short__iexact', 'bid__event__short__iexact'],
    'eventname'   : ['bid__speedrun__event__name__icontains', 'bid__event__name__icontains'],
    'locked'      : 'bid__event__locked',
    'run'         : 'bid__speedrun',
    'runname'     : 'bid__speedrun__name__icontains',
    'state'       : 'bid__state__iexact',
    'name'        : 'name__icontains',
  },
  'donationbid': {
    'event'         : 'donation__event',
    'eventshort'    : 'donation__event__short__iexact',
    'eventname'     : 'donation__event__name__icontains',
    'locked'        : 'donation__event__locked',
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
    'locked'       : 'event__locked',
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
  'donorcache': {
    'event'      : 'event',
    'firstname'  : 'donor__firstname__icontains',
    'lastname'   : 'donor__lastname__icontains',
    'alias'      : 'donor__alias__icontains',
    'email'      : 'donor__email__icontains',
    'visibility' : 'donor__visibility__iexact',
  },
  'event': {
    'name'        : 'name__icontains',
    'short'       : 'short__iexact',
    'locked'      : 'locked',
    'date_lte'    : 'date__lte',
    'date_gte'    : 'date__gte',
  },
  'prize': {
    'event'                : 'event',
    'eventname'            : 'event__name__icontains',
    'eventshort'           : 'event__short__iexact',
    'locked'               : 'event__locked',
    'category'             : 'category',
    'categoryname'         : 'category__name__icontains',
    'name'                 : 'name__icontains',
    'startrun'             : 'startrun',
    'endrun'               : 'endrun',
    'starttime_lte'        : ['starttime__lte', 'startrun__starttime__lte'],
    'starttime_gte'        : ['starttime__gte', 'startrun__starttime__gte'],
    'endtime_lte'          : ['endtime__lte', 'endrun__endtime__lte'],
    'endtime_gte'          : ['endtime__gte', 'endrun__endtime__gte'],
    'description'          : 'description__icontains',
    'shortdescription': 'shortdescription__icontains',
    'sumdonations'         : 'sumdonations',
    'randomdraw'           : 'randomdraw',
    'ticketdraw'           : 'ticketdraw',
    'state'                : 'state',
  },
  'prizeticket' : {
    'event'                : 'donation__event',
    'eventname'            : 'donation__event__name__icontains',
    'eventshort'           : 'donation__event__short__iexact',
    'prizename'            : 'prize__name__icontains',
    'prize'                : 'prize',
    'donation'             : 'donation',
    'donor'                : 'donation__donor',
    'amount'               : 'amount',
    'amount_lte'           : 'amount__lte',
    'amount_gte'           : 'amount__gte'
  },
  'prizewinner' : {
    'event'                : 'prize__event',
    'eventname'            : 'prize__event__name__icontains',
    'eventshort'           : 'prize__event__short__iexact',
    'prizename'            : 'prize__name__icontains',
    'prize'                : 'prize',
    'emailsent'            : 'emailsent',
    'winner'               : 'winner',
    'locked'               : 'prize__event__locked',
  },
  'prizecategory': {
    'name'        : 'name__icontains',
  },
  'prizeentry': {
    'donor'            : 'donor',
    'prize'            : 'prize',
    'prizename'        : 'prize__name__icontains',
    'event'            : 'prize__event',
    'eventname'        : 'prize__event__name__icontains',
    'eventshort'       : 'prize__event__short__iexact',
    'weight'           : 'weight',
    'weight_lte'       : 'weight__lte',
    'weight_gte'       : 'weight__gte',
    'locked'           : 'prize__event__locked',
  },
  'run': {
    'event'          : 'event',
    'eventname'      : 'event__name__icontains',
    'eventshort'     : 'event__short__iexact',
    'locked'         : 'event__locked',
    'name'           : 'name__icontains',
    'runner'         : 'runners',
    'runnername'     : 'runners__alias__icontains',
    'description'    : 'description__icontains',
    'starttime_lte'  : 'starttime__lte',
    'starttime_gte'  : 'starttime__gte',
    'endtime_lte'    : 'endtime__lte',
    'endtime_gte'    : 'endtime__gte',
  },
  'log': {
    'event'          : 'event',
    'eventname'      : 'event__name__icontains',
    'eventshort'     : 'event__short__iexact',
    'locked'         : 'event__locked',
    'category'       : 'category__iexact',
    'message'        : 'message__icontains',
    'timestamp_lte'  : 'timestamp__lte',
    'timestamp_gte'  : 'timestamp__gte',
  },
  'runner': { 
    'name'    : 'name',
    'stream'  : 'stream', 
    'twitter' : 'twitter', 
    'youtube' : 'youtube',
  },
}

_FKMap = {
  'winner': 'donor', 
  'speedrun': 'run',
  'startrun': 'run', 
  'endrun': 'run',
  'option': 'bid',
  'category': 'prizecategory', 
  'runners': 'donor', 
  'parent': 'bid', 
}

_DonorEmailFields = ['email', 'paypalemail']
_DonorNameFields = ['firstname', 'lastname']
_SpecialMarkers = ['icontains', 'contains', 'iexact', 'exact', 'lte', 'gte']

# additional considerations for permission related visibility at the 'field' level
def add_permissions_checks(rootmodel, key, query, user=None):
  toks = key.split('__')
  leading = ''
  if len(toks) >= 2:
    tail = toks[-2]
    ftail = _FKMap.get(tail,tail)
    rootmodel = ftail
    leading = '__'.join(toks[:-1]) + '__'
  field = toks[-1]
  if rootmodel == 'donor':
    visField = leading + 'visibility'
    if (field in _DonorEmailFields) and (user == None or not user.has_perm('tracker.view_emails')):
      # Here, we just want to remove the query altogether, since there is no circumstance that we want personal contact emails displayed publicly without permissions
      query = Q()
    elif (field in _DonorNameFields) and (user == None or not user.has_perm('tracker.view_usernames')):
      query &= Q(**{ visField: 'FULL' })
    elif (field == 'alias') and (user == None or not user.has_perm('tracker.view_usernames')):
      query &= Q(Q(**{ visField: 'FULL' }) | Q(**{ visField: 'ALIAS' }))
  elif rootmodel == 'donation':
    if (field == 'testdonation') and (user == None or not user.has_perm('tracker.view_test')):
      query = Q()
    if (field == 'comment') and (user == None or not user.has_perm('tracker.view_comments')):
      # only allow searching the textual content of approved comments
      commentStateField = leading + 'commentstate'
      query &= Q(**{ commentStateField: 'APPROVED' })
  elif rootmodel == 'bid':
    # Prevent 'hidden' bids from showing up in public queries
    if (field == 'state') and (user == None or not user.has_perm('tracker.view_hidden')):
      query &= ~Q(**{ key: 'HIDDEN' })
  return query

def recurse_keys(key, fromModels=[]):
  tail = key.split('__')[-1]
  ftail = _FKMap.get(tail,tail)
  if ftail in _GeneralFields:
    ret = []
    for key in _GeneralFields[ftail]:
      if key not in fromModels:
        fromModels.append(key)
        for k in recurse_keys(key, fromModels):
          ret.append(tail + '__' + k)
      return ret
  return [key]
  
def build_general_query_piece(rootmodel, key, text, user=None):
  if text:
    resultQuery = Q(**{ key + '__icontains': text })
    resultQuery = add_permissions_checks(rootmodel, key, resultQuery, user=user)
  else:
    resultQuery = Q()
  return resultQuery

def normalize_model_param(model):
  if model == 'speedrun':
    model = 'run'; # we should really just rename all instances of it already!
  if model not in _ModelMap:
    model = _ModelReverseMap[model]
  return model

# This creates a 'q'-esque Q-filter, similar to the search model of the django admin
def model_general_filter(model, text, user=None):
  fields = set()
  model = normalize_model_param(model)
  fromModels = [model]
  for key in _GeneralFields[model]:
    fields |= set(recurse_keys(key, fromModels=fromModels))
  fields = list(fields)
  query = Q()
  for field in fields:
    query |= build_general_query_piece(model, field, text, user=user)
  return query
  
# This creates a more specific filter, using UA's json API implementation as a basis
def model_specific_filter(model, searchDict, user=None):
  query = Q()
  model = normalize_model_param(model)
  modelSpecifics = _SpecificFields[model]
  for key in searchDict:
    if key in modelSpecifics:
      # A list/tuple of entries implies an 'or'-ing between all specified values
      # this isn't possible in the current url method, but it could be in the future if we had a way to encode lists (possibly by escaping commas in normal strings)
      values = searchDict[key]
      fieldQuery = Q()
      if isinstance(values, basestring) or not hasattr(values, '__iter__'):
        values = [values]
      for value in values:
        # allows modelspecific to be a single key, or multiple values 
        modelSpecific = modelSpecifics[key]
        if isinstance(modelSpecific, basestring) or not hasattr(modelSpecific, '__iter__'):
          modelSpecific = [modelSpecific]
        for searchKey in modelSpecific:
          fieldQuery |= Q( **{ searchKey: value })
      fieldQuery = add_permissions_checks(model, key, fieldQuery, user=user)
      query &= fieldQuery
  return query

def canonical_bool(b):
  if isinstance(b, basestring):
    if b.lower() in ['t', 'True', 'true', 'y', 'yes']:
      b = True
    elif b.lower() in ['f', 'False', 'false', 'n', 'no']:
      b = False
    else:
      b = None
  return b
  
def default_time(time):
  if time is None:
    time = datetime.utcnow()
  elif isinstance(time, basestring):
    time = dateutil.parser.parse(time)
  return time.replace(tzinfo=pytz.utc)

_DEFAULT_DONATION_DELTA = timedelta(hours=3)
_DEFAULT_DONATION_MAX = 200
_DEFAULT_DONATION_MIN = 25

# There is a slight complication in how this works, in that we cannot use the 'limit' set-up as a general filter mechanism, so these methods return the actual result, rather than a filter object
def get_recent_donations(donations=None, minDonations=_DEFAULT_DONATION_MIN, maxDonations=_DEFAULT_DONATION_MAX, delta=_DEFAULT_DONATION_DELTA, queryOffset=None):
  offset = default_time(queryOffset)
  if donations == None:
    donations = Donation.objects.all()
  if delta:
    highFilter = donations.filter(timereceived__gte=offset-delta)
  else:
    highFilter = donations
  count = highFilter.count()
  if maxDonations != None and count > maxDonations:
    donations = donations[:maxDonations]
  elif minDonations != None and count < minDonations:
    donations = donations[:minDonations]
  else:
    donations = highFilter
  return donations

_DEFAULT_RUN_DELTA = timedelta(hours=6)
_DEFAULT_RUN_MAX = 7
_DEFAULT_RUN_MIN = 3

def get_upcomming_runs(runs=None, includeCurrent=True, maxRuns=_DEFAULT_RUN_MAX, minRuns=_DEFAULT_RUN_MIN, delta=_DEFAULT_RUN_DELTA, queryOffset=None):
  offset = default_time(queryOffset)
  if runs == None:
    runs = SpeedRun.objects.all()
  if includeCurrent:
    runs = runs.filter(endtime__gte=offset)
  else:
    runs = runs.filter(starttime__gte=offset)
  if delta:
    highFilter = runs.filter(endtime__lte=offset+delta)
  else:
    highFilter = runs
  count = highFilter.count()
  if maxRuns != None and count > maxRuns:
    runs = runs[:maxRuns]
  elif minRuns != None and count < minRuns:
    runs = runs[:minRuns]
  else:
    runs = highFilter
  return runs

def get_future_runs(**kwargs):
  return get_upcomming_runs(includeCurrent=False, **kwargs)

def upcomming_bid_filter(**kwargs):
  runs = map(lambda run: run.id, get_upcomming_runs(SpeedRun.objects.filter(Q(bids__state='OPENED')).distinct(), **kwargs))
  return Q(speedrun__in=runs)

def get_upcomming_bids(**kwargs):
  return Bid.objects.filter(upcomming_bid_filter(**kwargs))
  
def future_bid_filter(**kwargs):
  return upcomming_bid_filter(includeCurrent=False, **kwargs)

def get_completed_bids(querySet, queryOffset=None):
  offset = default_time(queryOffset)
  return querySet.filter(state='OPENED').filter(Q(goal__isnull=False, total__gte=F('goal')) | Q(speedrun__isnull=False, speedrun__endtime__lte=offset) | Q(event__isnull=False, event__locked=True))
  
# Gets all of the current prizes that are possible right now (and also _sepcific_ to right now)
def concurrent_prizes_filter(runs):
  runCount = runs.count()
  if runCount == 0:
    return Q(id=None)
  startTime = runs[0].starttime
  endTime = runs.reverse()[0].endtime
  # yes, the filter query here is correct.  We want to get all prizes unwon prizes that _start_ before the last run in the list _ends_, and likewise all prizes that _end_ after the first run in the list _starts_.
  return Q(prizewinner__isnull=True) & (Q(startrun__starttime__lte=endTime, endrun__endtime__gte=startTime) | Q(starttime__lte=endTime, endtime__gte=startTime) | Q(startrun__isnull=True, endrun__isnull=True, starttime__isnull=True, endtime__isnull=True))
  
def current_prizes_filter(queryOffset=None):
  offset = default_time(queryOffset)
  return Q(prizewinner__isnull=True) & (Q(startrun__starttime__lte=offset, endrun__endtime__gte=offset) | Q(starttime__lte=offset, endtime__gte=offset) | Q(startrun__isnull=True, endrun__isnull=True, starttime__isnull=True, endtime__isnull=True))
  
def upcomming_prizes_filter(**kwargs):
  runs = get_upcomming_runs(**kwargs)
  return concurrent_prizes_filter(runs)
  
def future_prizes_filter(**kwargs):
  return upcomming_prizes_filter(includeCurrent=False, **kwargs)
  
def todraw_prizes_filter(queryOffset=None):
  offset = default_time(queryOffset)
  return Q(state='ACCEPTED') & (Q(prizewinner__isnull=True) & (Q(endrun__endtime__lte=offset) | Q(endtime__lte=offset) | (Q(endtime=None) & Q(endrun=None))))
  
def run_model_query(model, params={}, user=None, mode='user'):
  model = normalize_model_param(model)

  if model == 'log' and (mode != 'admin' or not user.has_perm('tracker.view_log')):
    return Log.objects.none() 
 
  filtered = _ModelMap[model].objects.all()
  
  filterAccumulator = Q()
  
  if model in _ModelDefaultQuery:
    filterAccumulator &= _ModelDefaultQuery[model]
  
  if 'id' in params:
    filterAccumulator &= Q(id=params['id'])
  if 'q' in params:
    filterAccumulator &= model_general_filter(model, params['q'], user=user)
  filterAccumulator &= model_specific_filter(model, params, user=user)
  if mode == 'user':
    filterAccumulator &= user_restriction_filter(model)
  filtered = filtered.filter(filterAccumulator)
  #filtered = filtered.distinct()

  if model in ['bid', 'bidtarget', 'allbids']:
    filtered = filtered.order_by(*Bid._meta.ordering)

  if 'feed' in params:
    filtered = apply_feed_filter(filtered, model, params['feed'], params, user=user)

  return filtered

def user_restriction_filter(model):
  if model == 'bid' or model == 'bidtarget' or model == 'allbids':
    return ~Q(state='HIDDEN')
  elif model == 'donation':
    return Q(transactionstate='COMPLETED', testdonation=F('event__usepaypalsandbox'))
  elif model == 'donor':
    return Q(donation__testdonation=F('donation__event__usepaypalsandbox'))
  elif model == 'prize':
    return Q(state='ACCEPTED')
  else:
    return Q()

def apply_feed_filter(query, model, feedName, params, user=None, noslice=False):
  if 'noslice' in params:
    noslice = canonical_bool(params['noslice'])
  if model == 'donation':
    if feedName == 'recent':
      callParams = { 'donations': query }
      if 'delta' in params:
        callParams['delta']  = timedelta(minutes=int(params['delta']))
      if 'offset' in params:
        callParams['queryOffset'] = default_time(params['offset'])
      if 'maxDonations' in params:
        callParams['maxDonations'] = int(params['maxDonations'])
      if 'minDonations' in params:
        callParams['minDonations'] = int(params['minDonations'])
      if noslice:
        callParams['maxDonations'] = None
        callParams['minDonations'] = None
      query = get_recent_donations(**callParams)
    elif feedName == 'toprocess':
      query = query.filter((Q(commentstate='PENDING') | Q(readstate='PENDING') | Q(bidstate='FLAGGED')) & Q(transactionstate='COMPLETED'))
    elif feedName == 'toread':
      query = query.filter(Q(readstate='READY') & Q(transactionstate='COMPLETED'))
  elif model in ['bid', 'bidtarget', 'allbids']:
    if feedName == 'open':
      query = query.filter(state='OPENED')
    elif feedName == 'closed':
      query = query.filter(state='CLOSED')
    elif feedName == 'current':
      callParams = {}
      if 'maxRuns' in params:
        callParams['maxRuns'] = int(params['maxRuns'])
      if 'minRuns' in params:
        callParams['minRuns'] = int(params['minRuns'])
      if 'delta' in params:
        callParams['delta'] = timedelta(minutes=int(params['delta']))
      if noslice:
        callParams['maxRuns'] = None
        callParams['minRuns'] = None
      if 'offset' in params:
        callParams['queryOffset'] = default_time(params['offset'])
      query = query.filter(state='OPENED').filter(upcomming_bid_filter(**callParams))
    elif feedName == 'future':
      callParams = {}
      if 'maxRuns' in params:
        callParams['maxRuns'] = int(params['maxRuns'])
      if 'minRuns' in params:
        callParams['minRuns'] = int(params['minRuns'])
      if noslice:
        callParams['maxRuns'] = None
        callParams['minRuns'] = None
      if 'delta' in params:
        callParams['delta'] = timedelta(minutes=int(toks[1]))
      if 'offset' in params:
        callParams['queryOffset'] = default_time(params['offset'])
      query = query.filter(future_bid_filter(**callParams))
    elif feedName == 'completed':
      query = get_completed_bids(query)
    elif feedName == 'suggested':
      query = query.filter(suggestions__isnull=False)
  elif model == 'run':
    callParams = { 'runs': query }
    if feedName == 'current':
      if 'maxRuns' in params:
        callParams['maxRuns'] = int(params['maxRuns'])
      if 'minRuns' in params:
        callParams['minRuns'] = int(params['minRuns'])
      if noslice:
        callParams['maxRuns'] = None
        callParams['minRuns'] = None
      if 'offset' in params:
        callParams['queryOffset'] = default_time(params['offset'])
      query = get_upcomming_runs(**callParams)
    elif feedName == 'future':
      if 'maxRuns' in params:
        callParams['maxRuns'] = int(params['maxRuns'])
      if 'minRuns' in params:
        callParams['minRuns'] = int(params['minRuns'])
      if noslice:
        callParams['maxRuns'] = None
        callParams['minRuns'] = None
      if 'delta' in params:
        callParams['delta'] = timedelta(minutes=int(params['delta']))
      if 'offset' in params:
        callParams['queryOffset'] = default_time(params['offset'])
      query = get_future_runs(**callParams)
  elif model == 'prize':
    if feedName == 'current':
      callParams = {}
      if 'offset' in params:
        callParams['queryOffset'] = default_time(params['offset'])
      query = query.filter(current_prizes_filter(**callParams))
    elif feedName == 'future':
      callParams = {}
      if 'maxRuns' in params:
        callParams['maxRuns'] = int(params['maxRuns'])
      if 'minRuns' in params:
        callParams['minRuns'] = int(params['minRuns'])
      if noslice:
        callParams['maxRuns'] = None
        callParams['minRuns'] = None
      if 'delta' in params:
        callParams['delta'] = timedelta(minutes=int(params['delta']))
      if 'offset' in params:
        callParams['queryOffset'] = default_time(params['offset'])
      x = upcomming_prizes_filter(**callParams)
      query = query.filter(x)
    elif feedName == 'won':
      query = query.filter(Q(prizewinner__isnull=False))
    elif feedName == 'unwon':
      query = query.filter(Q(prizewinner__isnull=True))
    elif feedName == 'todraw':
      query = query.filter(todraw_prizes_filter())
  elif model == 'bidsuggestion':
    if feedName == 'expired':
      query = query.filter(bid__state='CLOSED')
  elif model == 'event':
    if feedName == 'future':
        offsettime = default_time(params.get('offset', None))
        query = query.filter(date__gte=offsettime)
  return query
