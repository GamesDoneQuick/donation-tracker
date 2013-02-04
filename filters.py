from django.db.models import Q;
from tracker.models import *;
from datetime import *;
import pytz;

DEFAULT_RUN_DELTA = timedelta(hours=5);
DEFAULT_RUN_MAX = 7;
DEFAULT_RUN_MIN = 4;

# This is a pretty rough sketch of what I had in mind.  Obviously this will need
# to be refined over time as we discover our requirements, but I hope to make it
# robust enough that we can solve most of these problems by tweaking parameters

#TODO: the set of parameters used to filter the 'upcomming_runs' should probably
# be a structure, rather than just floating arguments, since then it'll be 
# easier to update the argument forwarding between the various things that use it

class EventFilter:
  def __init__(self, event):
    self.event = event;
    self.active_bids_q = Q(state='OPENED', speedrun__event=self.event);

  def upcomming_run_ids(self, delta=DEFAULT_RUN_DELTA, minRuns=DEFAULT_RUN_MIN, maxRuns=DEFAULT_RUN_MAX, offset=None):
    return list(map(lambda run: run.id, self.upcomming_runs(delta=delta, minRuns=minRuns, maxRuns=maxRuns, offset=offset)));

  def upcomming_runs(self, delta=DEFAULT_RUN_DELTA, minRuns=DEFAULT_RUN_MIN, maxRuns=DEFAULT_RUN_MAX, offset=None):
    if offset == None:
      offset = pytz.utc.localize(datetime.utcnow());
      print('fuck!');
    upcomming = SpeedRun.objects.filter(event=self.event, starttime__gte=offset)[:maxRuns];
    count = upcomming.count();
    if count > minRuns:
      upcomming = filter(lambda x: x.starttime <= offset+delta, upcomming);
    return list(upcomming);

  def active_choices(self):
    return Choice.objects.filter(self.active_bids_q);

  def active_challenges(self):
    return Challenge.objects.filter(self.active_bids_q);

  # The logic for these is currently a little weak, it just grabs all bids for any 'upcomming_runs', which means it might return absolutely no bids at all
  # A better strategy might be to grab all bids for at least the next 'x' runs, or grab bids until we have at least 'x' listed, rounded up to that games full set of bids.  I don't know, this will obviously require a lot of tweaking
  def upcomming_choices(self, delta=DEFAULT_RUN_DELTA, minRuns=DEFAULT_RUN_MIN, maxRuns=DEFAULT_RUN_MAX, offset=None):
    runIds = self.upcomming_run_ids(delta=delta, minRuns=minRuns, maxRuns=maxRuns, offset=offset);
    return Choice.objects.filter(self.active_bids_q, speedrun__in=runIds);

  def upcomming_challenges(self, delta=DEFAULT_RUN_DELTA, minRuns=DEFAULT_RUN_MIN,maxRuns=DEFAULT_RUN_MAX, offset=None):
    runIds = self.upcomming_run_ids(delta=delta, minRuns=minRuns, maxRuns=maxRuns, offset=offset);
    return Challenge.objects.filter(self.active_bids_q, speedrun__in=runIds);

  def upcomming_prizes(self, delta=DEFAULT_RUN_DELTA, minRuns=DEFAULT_RUN_MIN, maxRuns=DEFAULT_RUN_MAX, offset=None):
    runs = self.upcomming_runs(delta=delta, minRuns=minRuns, maxRuns=maxRuns, offset=offset);
    if len(runs) == 0:
      return [];
    runsLoTime = runs[0].starttime;
    runsHiTime = runs[-1].endtime;
    query = Q(startrun__starttime__gte=runsLoTime, endrun__endtime__lte=runsHiTime)# | Q(starttime__gte=runsLoTime, endtime__lte=runsHiTime);
    return Prize.objects.filter(query);

