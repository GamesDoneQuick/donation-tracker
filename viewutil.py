import re;
from tracker.models import *;
import filters;
from django.db.models import Count,Sum,Max,Avg,Q
import simplejson;
import random;
import gdata.spreadsheet.service;
import settings;
import datetime;
import dateutil.parser;

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
  seperators = [',',';','&','+',' and ',' or ', ' and/or ', ' vs. ']
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

def ParseGDocCellTitle(title):
  digit = re.search("\d", title);
  if not digit:
    return None;
  letters = title[:digit.start()];
  digits = title[digit.start():];
  columnIdx = 0;
  for letter in letters:
    if not re.match("[A-Z]", letter):
      return None;
    columnIdx *= 26;
    columnIdx += ord(letter) - ord('A');
  rowIdx = int(digits) - 1;
  return columnIdx, rowIdx;

def ParseGDocCellsHeaders(cells):
  headers = {};
  for cell in cells.entry:
    col,row = ParseGDocCellTitle(cell.title.text);
    if row > 0:
      break;
    while len(headers) < col:
      headers.append(None);
    headers[col] = cell.content.text.strip().lower();
  return headers;

def MakeEmptyRow(headers):
  row = {};
  for col in headers:
    row[headers[col]] = '';
  return row;

def ParseGDocCellsAsList(cells):
  headers = ParseGDocCellsHeaders(cells);
  currentRowId = 0;
  currentRow = MakeEmptyRow(headers);
  rows = [];
  for cell in cells.entry:
    col,row = ParseGDocCellTitle(cell.title.text);
    if row == 0:
      continue;
    if row != currentRowId and currentRowId != 0:
      rows.append(currentRow);
      currentRow = MakeEmptyRow(headers);
    currentRowId = row;
    if col in headers:
      currentRow[headers[col]] = cell.content.text;
  if currentRowId != 0:
    rows.append(currentRow);
  return rows;

def find_people(people_list):
  result = [];
  for person in people_list:
      try:
        d = Donor.objects.get(alias__iequals=person);
        result.append(d);
      except:
        pass;
  return result;

class MarathonSpreadSheetEntry:
    def __init__(self, name, time, estimate, runners=None, commentators=None, comments=None):
      self.gamename = name.lower()
      self.starttime = time
      self.endtime = estimate
      self.runners = runners or ''; # find_people(runners);
      self.commentators = commentators or ''; # find_people(commentators);
      self.comments = comments or ''
    def __unicode__(self):
      return self.gamename
    def __repr__(self):
      return u"MarathonSpreadSheetEntry('%s','%s','%s','%s','%s','%s')" % (self.starttime,
        self.gamename, self.runners, self.endtime, self.commentators, self.comments)

def ParseSpreadSheetEntry(event, rowEntries):
  estimatedTimeDelta = datetime.timedelta()
  postGameSetup = datetime.timedelta()
  comments = '';
  commentators = '';
  startTime = dateutil.parser.parse(rowEntries[event.scheduledatetimefield]);
  gameName = rowEntries[event.schedulegamefield]
  runners = rowEntries[event.schedulerunnersfield]; # natural_list_parse(rowEntries[event.schedulerunnersfield])
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
    commentators = rowEntries[event.schedulecommentatorsfield] # natural_list_parse(rowEntries[event.schedulecommentatorsfield]);
  if event.schedulecommentsfield:
    comments = rowEntries[event.schedulecommentsfield]
  estimatedTime = startTime + estimatedTimeDelta
  # Convert the times into UTC
  timezone = pytz.timezone(event.scheduletimezone);
  startTime = timezone.localize(startTime)
  estimatedTime = timezone.localize(estimatedTime)
  ret = MarathonSpreadSheetEntry(gameName, startTime, estimatedTime+postGameSetup, runners, commentators, comments);
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

def MergeScheduleGDoc(event):
  # This is required by the gdoc api to identify the name of the application making the request, but it can basically be any string
  PROGRAM_NAME = "sda-webtracker"
  spreadsheetService = gdata.spreadsheet.service.SpreadsheetsService()
  spreadsheetService.ClientLogin(settings.GDOC_USERNAME, settings.GDOC_PASSWORD)
  cellFeed = spreadsheetService.GetCellsFeed(key=event.scheduleid)
  try:
    runs = filter(lambda r: r.gamename.strip() and 'setup' not in r.gamename.lower() and 'end' not in r.gamename.lower() and 'start' not in r.gamename.lower(), map(lambda x: ParseSpreadSheetEntry(event, x), ParseGDocCellsAsList(cellFeed)))
  except KeyError:
    raise Exception('KeyError, make sure the column names are correct');
  existingruns = dict(map(lambda r: (r.name.lower(),r),SpeedRun.objects.filter(event=event)))
  sortkey = 0;
  prizesortkey = 0;
  for run in runs:
    r = existingruns.get(run.gamename,SpeedRun(name=run.gamename,event=event,description=run.comments))
    r.sortkey = sortkey
    r.deprecated_runners = run.runners;
    #for runner in run.runners:
    #  r.runners.add(runner);
    r.starttime = run.starttime
    r.endtime = run.endtime
    r.save()
    sortkey += 1
  prizes = sorted(Prize.objects.filter(event=event),cmp=prizecmp)
  sortkey = 0
  for p in prizes:
    p.sortkey = prizesortkey
    p.save()
    prizesortkey += 1;
  return len(runs);
  
EVENT_SELECT = 'admin-event';

def get_selected_event(request):
  evId = request.session.get(EVENT_SELECT, None);
  if evId:
    return Event.objects.get(pk=evId);
  else:
    return None;

def set_selected_event(request, event):
  if event:
    request.session[EVENT_SELECT] = event.id;
  else:
    request.session[EVENT_SELECT] = None;

