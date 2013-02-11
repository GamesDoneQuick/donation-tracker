from django.db.models import Q;
from tracker.models import *;
from datetime import *;
import pytz;

def text_filter(fields, searchString):
  query = Q();
  if searchString:
    for field in fields:
      query |= Q(**{field + "__icontains": searchString});
  return query;

# now that I think about it, searching by donor identifier stuff may be a sensitive issue...
"""
_DONOR_FIELDS = ['email', 'alias'];
def donor_filter(searchString):
  customFirstNameFilter = Q(firstname__icontains=searchString) & ~Q(anonymous=True);
  customLastNameFilter = Q(lastname__icontains=searchString) & ~Q(anonymous=True);
  return customFirstNameFilter & customLastNameFilter & text_filter(_DONOR_FIELDS, searchString);

def public_donation_filter(searchString):
  customCommentFilter = Q(comment=searchString) & ~Q(commentstate='DENIED');
"""
  
_RUN_FILTER_FIELDS = ['name', 'runners', 'description'];
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
      self.all_donations_q &= Q(event=self.event); 

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
    return Donor.objects.filter(self.all_donors_q);

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

 
