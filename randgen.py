import random;
import decimal
from tracker.models import *;
import datetime;
import pytz;

def RandomName(rand, base):
  return base + str(rand.getrandbits(32));

def RandomEventName(rand):
  return RandomName(rand, 'event');

def RandomFirstName(rand):
  return RandomName(rand, 'first');

def RandomLastName(rand):
  return RandomName(rand, 'last');

def RandomAlias(rand):
  return RandomName(rand, 'alias');

def RandomEmail(rand, base):
  return base + '@gmail.com';

def RandomPaypalEmail(rand, base, otherEmail):
  result = otherEmail;
  while result == otherEmail:
    result = RandomName(rand, base) + '@gmail.com';

def RandomTwitch(rand, base):
  return 'http://twitch.tv/' + base;

def RandomYoutube(rand, base):
  return 'http://youtube.com/' + base;

def RandomWebsite(rand, base):
  return 'http://' + base + '.com';

def RandomTwitter(rand, base):
   return '@' + base;

def RandomGameName(rand):
  return 'game' + str(rand.getrandbits(32));

def RandomGameDescription(rand, gamename):
  return 'Description for ' + gamename;

def RandomPrizeName(rand, forGame=None):
  prizename = 'prize' + str(rand.getrandbits(32));
  if forGame:
    prizename = forGame + prizename;
  return prizename;

def RandomPrizeDescription(rand, prizename):
  return 'Description for ' + prizename;

# this may make more sense in the 'generate character name', 'generate challenge name', 'generate binary choice', etc... sense
def RandomBidName(rand):
  return 'bid' + str(rand.getrandbits(32)); 

def RandomBidDescription(rand, bidname):
  return 'Description for ' + bidname;

def RandomAmount(rand, rounded=True, minAmount=decimal.Decimal('0.00'), maxAmount=decimal.Decimal('10000.00')):
  drange = maxAmount - minAmount;
  return (minAmount + (drange * decimal.Decimal(rand.random()))).quantize(decimal.Decimal('.01'), rounding=decimal.ROUND_UP);
  
def RandomTime(rand, start, end):
  delta = end - start;
  result = start + datetime.timedelta(seconds=rand.randrange(delta.total_seconds()));
  return result.replace(tzinfo = pytz.utc);

def PickRandomFromQueryset(rand, q):
  num = q.count();
  return q[rand.randrange(num)];

def PickRandomElement(rand, l):
  return rand.choice(l);

def PickRandomInstance(rand, model):
  num = model.objects.all().count();
  return model.objects.all()[rand.randrange(num)];

def TrooleanCheck(rand, value):
  if value == True or value == False:
    return value;
  else:
    return bool(rand.getrandbits(1));

def GenerateDonor(rand):
  donor = Donor();
  donor.firstname = RandomFirstName(rand);
  donor.lastname = RandomLastName(rand);
  alias = RandomAlias(rand);
  if rand.getrandbits(1):
    donor.alias = alias;
  donor.email = RandomEmail(rand, alias);
  if rand.getrandbits(1):
    donor.paypalemail = RandomPaypalEmail(rand, alias, donor.email);
  donor.visibility = PickRandomElement(rand, DonorVisibilityChoices)[0];
  return donor;

_DEFAULT_MAX_RUN_LENGTH=3600*6;

def GenerateRun(rand, startTime, event=None, maxRunLength=_DEFAULT_MAX_RUN_LENGTH):
  run = SpeedRun();
  run.name = RandomGameName(rand); 
  run.description = RandomGameDescription(rand, run.name);
  run.starttime = startTime;
  run.endtime = startTime + datetime.timedelta(seconds=rand.randrange(maxRunLength));
  run.sortkey = 0;
  if event:
    run.event = event;
  else:
    run.event = PickRandomInstance(rand, Event);
  return run;

def GeneratePrize(rand, category=None, event=None, useRun=None, startRun=None, endRun=None, startTime=None, endTime=None, sumDonations=None, minAmount=Decimal('1.00'), maxAmount=Decimal('20.00'), randomDraw=None):
  prize = Prize();
  prize.name = RandomPrizeName(rand);
  prize.description = RandomPrizeDescription(rand, prize.name);
  prize.sortkey = 0;
  if startRun:
    prize.startrun = startRun;
    prize.endrun = endRun;
  elif startTime:
    prize.starttime = startTime;
    prize.endtime = endTime;  
  if category:
    prize.category = category;
  else:
    prize.category = PickRandomInstance(rand, PrizeCategory);
  if not TrooleanCheck(rand, sumDonations):
    prize.sumdonations = True;
    valA = RandomAmount(rand, minAmount=minAmount, maxAmount=maxAmount);
    valB = RandomAmount(rand, minAmount=minAmount, maxAmount=maxAmount);
    prize.minimumbid = min(valA, valB);
    prize.maximumbid = max(valA, valB);
  else:
    prize.minimumbid = prize.maximumbid = RandomAmount(rand, minAmount=minAmount, maxAmount=maxAmount);
  if TrooleanCheck(rand, randomDraw):
    prize.randomDraw = False;
  if startRun != None:
    prize.event = startRun.event;
  elif event:
    prize.event = event;
  else:
    prize.event = PickRandomInstance(rand, Event);

  return prize;

def GenerateBid(rand, allowChildren=None, maxChildren=5, maxDepth=2, addGoal=None, minGoal=decimal.Decimal('0.01'), maxGoal=decimal.Decimal('1000.00'), run=None, event=None, parent=None, state=None):
  bid = Bid();
  bid.name = RandomBidName(rand); 
  bid.description = RandomBidDescription(rand, bid.name);
  if TrooleanCheck(rand, addGoal):
    bid.goal = RandomAmount(rand, minAmount=minGoal, maxAmount=maxGoal);
  children = [];
  if maxDepth > 0 and TrooleanCheck(rand, allowChildren):
    numChildren = rand.randrange(maxChildren);
    for c in range(0, numChildren):
      children.append(GenerateBid(rand, allowChildren=False, maxDepth=maxDepth-1, addGoal=addGoal, minGoal=minGoal, maxGoal=maxGoal, run=run, event=event, parent=bid, state=state)); 
    bid.istarget = False;
  else:
    bid.istarget = True;
  if not run and not event and not parent:
    raise Exception('Fuck off');
  if parent:
    bid.parent = parent;
  if run:
    bid.speedrun = run;
  if event:
    bid.event = event;
  if state:
    bid.state = state;
  else:
    bid.state = PickRandomElement(rand, Bid._meta.get_field('state').choices)[0]; 
  return bid, children;

def ChainInsertBid(bid, children):
  bid.save();
  for child in children:
    ChainInsertBid(child[0], child[1]);

def GenerateDonation(rand, donor=None, domain=None, event=None, minAmount=decimal.Decimal('0.01'), maxAmount=decimal.Decimal('1000.00'), minTime=None, maxTime=None): 
  donation = Donation();
  donation.amount = RandomAmount(rand, minAmount=minAmount, maxAmount=maxAmount);
  if event:
    donation.event = event;
  else:
    donation.event = PickRandomInstance(rand, Event);
  if domain:
    donation.domain = domain;
  else:
    donation.domain = PickRandomElement(rand, DonationDomainChoices)[0];
  donation.domainId = str(rand.getrandbits(64));
  donation.amount = RandomAmount(rand, minAmount=minAmount, maxAmount=maxAmount);
  donation.fee = (donation.amount * decimal.Decimal(0.03)).quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_UP);
  donation.comment = RandomName(rand, 'Comment');
  if not minTime:
    minTime = datetime.datetime.combine(donation.event.date, datetime.datetime.min.time());
  if not maxTime:
    maxTime = minTime + datetime.timedelta(seconds=60*60*24*14);
  donation.timereceived = RandomTime(rand, minTime, maxTime); 
  donation.currency = 'USD';
  donation.testdonation = event.usepaypalsandbox;
  donation.transactionstate = 'COMPLETED';
  if not donor:
    donor = PickRandomInstance(rand, Donor);
  donation.donor = donor;
  return donation;

def GenerateEvent(rand, startTime=None):
  event = Event();
  if not startTime:
    startTime = datetime.datetime.utcnow().replace(tzinfo=pytz.utc);
  event.date = startTime.date();
  event.name = RandomEventName(rand);
  event.short = event.name;
  event.targetamount = Decimal('1000.00');
  return event;

def GetBidTargets(bid, children):
  targets = [];
  for child in children:
    targets.extend(GetBidTargets(child[0], child[1]));
  if bid.istarget:
    targets.append(bid);
  return targets;

def AssignBids(rand, donation, fromSet):
  amount = RandomAmount(rand, maxAmount=donation.amount);
  while amount > Decimal('0.00') and len(fromSet) > 0:
    if amount < Decimal('1.00') or rand.getrandbits(1) == 1:
      useAmount = amount; 
    else:
      useAmount = RandomAmount(rand, minAmount=Decimal('1.00'), maxAmount=amount);
    amount = amount - useAmount;
    bid = rand.choice(fromSet);
    DonationBid.objects.create(donation=donation, bid=bid, amount=useAmount);

def BuildRandomEvent(rand, numDonors, numDonations, numRuns, numBids, numPrizes, startTime):
  startTime = startTime.replace(tzinfo=pytz.utc);
  
  if not PrizeCategory.objects.all().exists():
    PrizeCategory.objects.create(name='Game');
    PrizeCategory.objects.create(name='Grand');
    PrizeCategory.objects.create(name='Grab Bag');

  event = GenerateEvent(rand, startTime=startTime);
  event.save();
  lastRunTime = startTime;
  listOfRuns = [];
  for i in range(0, numRuns):
    run = GenerateRun(rand, startTime=lastRunTime, event=event);
    lastRunTime = run.endtime;
    run.save();
    listOfRuns.append(run);
  listOfDonors = [];
  for i in range(0, numDonors):
    donor = GenerateDonor(rand);
    donor.save();
    listOfDonors.append(donor);
  topBidsList = [];
  bidTargetsList = [];
  for i in range(0, numBids):
    if rand.getrandbits(2) <= 2:
      bid, children = GenerateBid(rand, run=PickRandomElement(rand, listOfRuns));
    else:
      bid, children = GenerateBid(rand, event=event);
    ChainInsertBid(bid, children);
    topBidsList.append(bid);
    bidTargetsList.extend(GetBidTargets(bid, children));

  for i in range(0, numPrizes):
    if rand.getrandbits(2) <= 2:
      distance = rand.randrange(min(6, numRuns));
      startRunId = rand.randrange(numRuns - distance);
      endRunId = startRunId + distance;
      prize = GeneratePrize(rand, event=event, startRun=listOfRuns[startRunId], endRun=listOfRuns[endRunId]);
    else:
      time0 = RandomTime(rand, startTime, lastRunTime);
      time1 = RandomTime(rand, startTime, lastRunTime);
      start = min(time0, time1);
      end = max(time0, time1);
      prize = GeneratePrize(rand, event=event, startTime=start, endTime=end);
    prize.save();
  for i in range(0, numDonations):
    donation = GenerateDonation(rand, event=event, minTime=startTime, maxTime=lastRunTime);
    donation.save(); 
    AssignBids(rand, donation, bidTargetsList);
  return event;

