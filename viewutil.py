from decimal import Decimal
import random
import httplib2
import re
import pytz
import operator
import datetime
import dateutil.parser

from oauth2client.file import Storage
import gdata.spreadsheet.service

from django.db.models import Count,Sum,Max,Avg,Q
from django.core.urlresolvers import reverse
from django.http import Http404
from django.contrib.auth import get_user_model
from django.db import transaction

import settings

from tracker.models import *
import tracker.filters as filters
import tracker.util as util


def get_default_email_host_user():
  return getattr(settings, 'EMAIL_HOST_USER', '')

def get_default_email_from_user():
  return getattr(settings, 'EMAIL_FROM_USER', get_default_email_host_user())
  
def admin_url(obj):
  return reverse("admin:%s_%s_change" % (obj._meta.app_label, obj._meta.object_name.lower()), args=(obj.pk,), current_app=obj._meta.app_label)

# Adapted from http://djangosnippets.org/snippets/1474/
def get_request_server_url(request):
    if request:
        serverName = request.META['SERVER_NAME']
        protocol = "https://" if request.is_secure() else "http://"
        return protocol + serverName
    else:
        raise Exception("Request was null.")

def get_referer_site(request):
  origin = request.META.get('HTTP_ORIGIN', None)
  if origin != None:
    return re.sub(r'^https?:\/\/', '', origin)
  else:
    return None

def get_event(event):
  if event:
    if isinstance(event, Event):
        return event
    try:
      if re.match(r'^\d+$', event):
        return Event.objects.get(id=event)
      else:
        return Event.objects.get(short=event)
    except Event.DoesNotExist:
      raise Http404
  e = Event()
  e.id = None
  e.name = 'All Events'
  return e

def request_params(request):
  if request.method == 'GET':
    return request.GET
  elif request.method == 'POST':
    return request.POST
  else:
    raise Exception("No request parameters associated with this request method.")

def draw_prize(prize, seed=None):
  eligible = prize.eligible_donors()
  if prize.maxed_winners():
    if prize.maxwinners == 1:
      return False, { "error" : "Prize: " + prize.name + " already has a winner." }
    else:
      return False, { "error" : "Prize: " + prize.name + " already has the maximum number of winners allowed." }
  if not eligible:
    return False, { "error" : "Prize: " + prize.name + " has no eligible donors." }
  else:
    rand = None
    try:
      rand = random.Random(seed)
    except TypeError: # not sure how this could happen but hey
      return False, {'error': 'Seed parameter was unhashable'}
    psum = reduce(lambda a,b: a+b['weight'], eligible, 0.0)
    result = rand.random() * psum
    ret = {'sum': psum, 'result': result}
    for d in eligible:
      if result < d['weight']:
        try:
          donor = Donor.objects.get(pk=d['donor'])
          acceptDeadline = datetime.datetime.today().replace(tzinfo=util.anywhere_on_earth_tz(), hour=23, minute=59, second=59) + datetime.timedelta(days=prize.event.prize_accept_deadline_delta)
          winRecord,created = PrizeWinner.objects.get_or_create(prize=prize, winner=donor, acceptdeadline=acceptDeadline)
          if not created:
            winRecord.pendingcount += 1
          ret['winner'] = winRecord.winner.id
          winRecord.save()
        except Exception as e:
          return False, { "error" : "Error drawing prize: " + prize.name + ", " + str(e) }
        return True, ret
      result -= d['weight']
    return False, {"error" : "Prize drawing algorithm failed." }

_1ToManyBidsAggregateFilter = Q(bids__donation__transactionstate='COMPLETED')
_1ToManyDonationAggregateFilter = Q(donation__transactionstate='COMPLETED')
DonationBidAggregateFilter = _1ToManyDonationAggregateFilter
DonorAggregateFilter = _1ToManyDonationAggregateFilter
EventAggregateFilter = _1ToManyDonationAggregateFilter
PrizeWinnersFilter = Q(prizewinner__acceptcount_gt=0) | Q(prizewinner__pendingcount__gt=0)

# http://stackoverflow.com/questions/5722767/django-mptt-get-descendants-for-a-list-of-nodes
def get_tree_queryset_descendants(model, nodes, include_self=False):
  if not nodes:
    return nodes
  filters = []
  for n in nodes:
    lft, rght = n.lft, n.rght
    if include_self:
      lft -=1
      rght += 1
    filters.append(Q(tree_id=n.tree_id, lft__gt=lft, rght__lt=rght))
  q = reduce(operator.or_, filters)
  return model.objects.filter(q).order_by(*model._meta.ordering)

# http://stackoverflow.com/questions/6471354/efficient-function-to-retrieve-a-queryset-of-ancestors-of-an-mptt-queryset
def get_tree_queryset_ancestors(model, nodes):
  tree_list = {}
  query = Q()
  for node in nodes:
    if node.tree_id not in tree_list:
      tree_list[node.tree_id] = []
    parent =  node.parent.pk if node.parent is not None else None,
    if parent not in tree_list[node.tree_id]:
      tree_list[node.tree_id].append(parent)
      query |= Q(lft__lt=node.lft, rght__gt=node.rght, tree_id=node.tree_id)
    return model.objects.filter(query).order_by(*model._meta.ordering)

def get_tree_queryset_all(model, nodes):
  filters = []
  for node in nodes:
    filters.append(Q(tree_id=node.tree_id))
  q = reduce(operator.or_, filters)
  return model.objects.filter(q).order_by(*model._meta.ordering)

ModelAnnotations = {
  'event'        : { 'amount': Sum('donation__amount', only=EventAggregateFilter), 'count': Count('donation', only=EventAggregateFilter), 'max': Max('donation__amount', only=EventAggregateFilter), 'avg': Avg('donation__amount', only=EventAggregateFilter) },
  'prize' : { 'numwinners': Count('prizewinner', only=PrizeWinnersFilter), },
}

def parse_gdoc_cell_title(title):
  digit = re.search("\d", title)
  if not digit:
    return None
  letters = title[:digit.start()]
  digits = title[digit.start():]
  columnIdx = 0
  for letter in letters:
    if not re.match("[A-Z]", letter):
      return None
    columnIdx *= 26
    columnIdx += ord(letter) - ord('A')
  rowIdx = int(digits) - 1
  return columnIdx, rowIdx

def parse_gdoc_cell_headers(cells):
  headers = {}
  for cell in cells.entry:
    col,row = parse_gdoc_cell_title(cell.title.text)
    if row > 0:
      break
    headers[col] = cell.content.text.strip().lower()
  return headers

def make_empty_row(headers):
  row = {}
  for col in headers:
    row[headers[col]] = ''
  return row

def parse_gdoc_cells_as_list(cells):
  headers = parse_gdoc_cell_headers(cells)
  currentRowId = 0
  currentRow = make_empty_row(headers)
  rows = []
  for cell in cells.entry:
    col,row = parse_gdoc_cell_title(cell.title.text)
    if row == 0:
      continue
    if row != currentRowId and currentRowId != 0:
      rows.append(currentRow)
      currentRow = make_empty_row(headers)
    currentRowId = row
    if col in headers:
      currentRow[headers[col]] = cell.content.text
  if currentRowId != 0:
    rows.append(currentRow)
  return rows

def find_people(people_list):
  result = []
  for person in people_list:
      try:
        d = Donor.objects.get(alias__iequals=person)
        result.append(d)
      except:
        pass
  return result

class MarathonSpreadSheetEntry:
    def __init__(self, name, time, estimate, runners=None, commentators=None, comments=None):
      self.gamename = name
      self.starttime = time
      self.endtime = estimate
      self.runners = runners or ''; # find_people(runners)
      self.commentators = commentators or ''; # find_people(commentators)
      self.comments = comments or ''
    def __unicode__(self):
      return self.gamename
    def __repr__(self):
      return u"MarathonSpreadSheetEntry('%s','%s','%s','%s','%s','%s')" % (self.starttime,
        self.gamename, self.runners, self.endtime, self.commentators, self.comments)

def parse_row_entry(event, rowEntries):
  estimatedTimeDelta = datetime.timedelta()
  postGameSetup = datetime.timedelta()
  comments = ''
  commentators = ''
  if rowEntries[event.scheduledatetimefield]:
    startTime = dateutil.parser.parse(rowEntries[event.scheduledatetimefield])
  else:
    return None
  gameName = rowEntries[event.schedulegamefield].strip()

  canonicalGameNameForm = gameName.lower()

  if not canonicalGameNameForm or canonicalGameNameForm in ['start', 'end', 'finale', 'total:'] or 'setup' in canonicalGameNameForm:
    return None

  runners = rowEntries[event.schedulerunnersfield];
  if event.scheduleestimatefield and rowEntries[event.scheduleestimatefield]:
    toks = rowEntries[event.scheduleestimatefield].split(":")
    if len(toks) == 3:
      estimatedTimeDelta = datetime.timedelta(hours=int(toks[0]), minutes=int(toks[1]), seconds=int(toks[2]))
  # I'm not sure what should be done with the post-game set-up field...
  if event.schedulesetupfield:
    if rowEntries[event.schedulesetupfield]:
      toks = rowEntries[event.schedulesetupfield].split(":")
      if len(toks) == 3:
        postGameSetup = datetime.timedelta(hours=int(toks[0]), minutes=int(toks[1]), seconds=int(toks[2]))
  if event.schedulecommentatorsfield:
    commentators = rowEntries[event.schedulecommentatorsfield]
  if event.schedulecommentsfield:
    comments = rowEntries[event.schedulecommentsfield]
  estimatedTime = startTime + estimatedTimeDelta
  # Convert the times into UTC
  timezone = pytz.timezone(event.scheduletimezone)
  startTime = timezone.localize(startTime)
  estimatedTime = timezone.localize(estimatedTime)
  ret = MarathonSpreadSheetEntry(gameName, startTime, estimatedTime+postGameSetup, runners, commentators, comments)
  return ret


def prizecmp(a,b):
  # if both prizes are run-linked, sort them that way
  if a.startrun and b.startrun:
    return cmp(a.startrun.starttime,b.startrun.starttime) or cmp(a.endrun.endtime,b.endrun.endtime) or cmp(a.name,b.name)
  # else if they're both time-linked, sort them that way
  if a.starttime and b.starttime:
    return cmp(a.starttime,b.starttime) or cmp(a.endtime,b.endtime) or cmp(a.name,b.name)
  # run-linked prizes are listed after time-linked and non-linked
  if a.startrun and not b.startrun:
    return 1
  if b.startrun and not a.startrun:
    return -1
  # time-linked prizes are listed after non-linked
  if a.starttime and not b.starttime:
    return 1
  if b.starttime and not a.starttime:
    return -1
  # sort by category or name as a fallback
  return cmp(a.category,b.category) or cmp(a.name,b.name)

def merge_schedule_list(event, scheduleList):
  try:
    runs = filter(lambda r: r != None, map(lambda x: parse_row_entry(event, x), scheduleList))
  except KeyError, k:
    raise Exception('KeyError, \'%s\' make sure the column names are correct' % k.args[0])
  existingruns = dict(map(lambda r: (r.name.lower(),r),SpeedRun.objects.filter(event=event)))

  scheduleRunNames = set()
  addedRuns = []

  for run in runs:
    uniqueGameName = run.gamename.lower()
    if uniqueGameName in scheduleRunNames:
      raise Exception('Merged schedule has two runs with the same name \'%s\'' % uniqueGameName)
    scheduleRunNames.add(uniqueGameName)
    if uniqueGameName in existingruns.keys():
      r = existingruns[uniqueGameName]
    else:
      r = SpeedRun(name=run.gamename, event=event, description=run.comments)
      addedRuns.append(r)
    r.name = run.gamename
    r.deprecated_runners = run.runners
    #for runner in run.runners:
    #  r.runners.add(runner)
    r.starttime = run.starttime
    r.endtime = run.endtime
    r.save()

  removedRuns = []

  for existingRunName, existingRun in existingruns.items():
    if existingRunName not in scheduleRunNames:
      removedRuns.append(existingRun)

  # Eventually we may want to have something that asks for user descisions regarding runs added/removed
  # from the schdule, for now, we take the schedule as cannon
  for run in removedRuns:
    run.delete()

  prizes = sorted(Prize.objects.filter(event=event),cmp=prizecmp)
  return len(runs)

def merge_schedule_gdoc(event, username=None):
  # This is required by the gdoc api to identify the name of the application making the request, but it can basically be any string
  PROGRAM_NAME = "sda-webtracker"
  # try:
  #   credentials = CredentialsModel.objects.get(id__username=username).credentials
  # except CredentialsModel.DoesNotExist:
  storage = Storage('creds.dat')
  credentials = storage.get()
  if credentials.access_token_expired:
    credentials.refresh(httplib2.Http())
  spreadsheetService = gdata.spreadsheet.service.SpreadsheetsService(additional_headers={'Authorization' : 'Bearer %s' % credentials.access_token})
  #  spreadsheetService.ClientLogin(settings.GDOC_USERNAME, settings.GDOC_PASSWORD)
  cellFeed = spreadsheetService.GetCellsFeed(key=event.scheduleid)
  return merge_schedule_list(event, parse_gdoc_cells_as_list(cellFeed))

EVENT_SELECT = 'admin-event'

def get_selected_event(request):
  evId = request.session.get(EVENT_SELECT, None)
  if evId:
    return Event.objects.get(pk=evId)
  else:
    return None

def set_selected_event(request, event):
  if event:
    request.session[EVENT_SELECT] = event.id
  else:
    request.session[EVENT_SELECT] = None

def get_donation_prize_contribution(prize, donation, secondaryAmount=None):
  if prize.contains_draw_time(donation.timereceived):
    amount = secondaryAmount if secondaryAmount != None else donation.amount
    if prize.sumdonations or amount >= prize.minimumbid:
      return amount
  return None

def get_donation_prize_info(donation):
  """ Attempts to find a list of all prizes this donation gives the donor eligibility for.
    Does _not_ attempt to relate this information to any _past_ eligibility.
    Returns the set as a list of {'prize','amount'} dictionaries. """
  prizeList = []
  for ticket in donation.tickets.all():
    contribAmount = get_donation_prize_contribution(ticket.prize, donation, ticket.amount)
    if contribAmount != None:
      prizeList.append({'prize': ticket.prize, 'amount': contribAmount})
  for timeprize in filters.run_model_query( 'prize', params={ 'feed': 'current', 'ticketdraw': False, 'offset': donation.timereceived, 'noslice': True } ):
    contribAmount = get_donation_prize_contribution(timeprize, donation)
    if contribAmount != None:
      prizeList.append({'prize': timeprize, 'amount': contribAmount})
  return prizeList

def tracker_log(category, message='', event=None, user=None):
  Log.objects.create(category=category, message=message, event=event, user=user)

def merge_bids(rootBid, bids):
  for bid in bids:
    if bid != rootBid:
      for donationBid in bid.bids.all():
        donationBid.bid = rootBid
        donationBid.save()
      for suggestion in bid.suggestions.all():
        suggestion.bid = rootBid
        suggestion.save()
      bid.delete()
  rootBid.save()
  return rootBid

def merge_donors(rootDonor, donors):
  for other in donors:
    if other != rootDonor:
      for donation in other.donation_set.all():
        donation.donor = rootDonor
        donation.save()
      for prizewin in other.prizewinner_set.all():
        prizewin.winner = rootDonor
        prizewin.save()
      other.delete()
  rootDonor.save()
  return rootDonor

def autocreate_donor_user(donor):
    AuthUser = get_user_model()
    
    if not donor.user:
        with transaction.atomic():
            linkUser = None
            try:
                linkUser = AuthUser.objects.get(email=donor.email)
            except AuthUser.MultipleObjectsReturned:
                message = 'Multiple users found for email {0}, when trying to mail donor {1} for prizes'.format(donor.email, donor.id)
                tracker_log('prize', message, event=event)
                raise Exception(message)
            except AuthUser.DoesNotExist:
                targetUsername = donor.email
                if donor.alias and not AuthUser.objects.filter(username=donor.alias):
                    targetUsername = donor.alias
                linkUser = AuthUser.objects.create(username=targetUsername, email=donor.email, first_name=donor.firstname, last_name=donor.lastname, is_active=False)
            donor.user = linkUser
            donor.save()
        
    return donor.user
