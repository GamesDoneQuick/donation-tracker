from django.db import models
from django.core.exceptions import ValidationError

from tracker.validators import *
from event import Event

from decimal import Decimal

__all__ = [
  'Prize',
  'PrizeTicket',
  'PrizeWinner',
  'PrizeCategory',
]

def LatestEvent():
  try:
    return Event.objects.latest()
  except Event.DoesNotExist:
    return None

class PrizeManager(models.Manager):
  def get_by_natural_key(self, name, event):
    return self.get(name=name,event=Event.objects.get_by_natural_key(*event))

class Prize(models.Model):
  objects = PrizeManager()
  name = models.CharField(max_length=64)
  category = models.ForeignKey('PrizeCategory',null=True,blank=True)
  image = models.URLField(max_length=1024,null=True,blank=True)
  description = models.TextField(max_length=1024,null=True,blank=True)
  minimumbid = models.DecimalField(decimal_places=2,max_digits=20,default=Decimal('5.0'),verbose_name='Minimum Bid',validators=[positive,nonzero])
  maximumbid = models.DecimalField(decimal_places=2,max_digits=20,null=True,blank=True,default=Decimal('5.0'),verbose_name='Maximum Bid',validators=[positive,nonzero])
  sumdonations = models.BooleanField(default=False,verbose_name='Sum Donations')
  randomdraw = models.BooleanField(default=True,verbose_name='Random Draw')
  ticketdraw = models.BooleanField(default=False,verbose_name='Ticket Draw');
  event = models.ForeignKey('Event', default=LatestEvent)
  startrun = models.ForeignKey('SpeedRun',related_name='prize_start',null=True,blank=True,verbose_name='Start Run')
  endrun = models.ForeignKey('SpeedRun',related_name='prize_end',null=True,blank=True,verbose_name='End Run')
  starttime = models.DateTimeField(null=True,blank=True,verbose_name='Start Time')
  endtime = models.DateTimeField(null=True,blank=True,verbose_name='End Time')
  winners = models.ManyToManyField('Donor', related_name='prizeswon', blank=True, null=True, through='PrizeWinner')
  maxwinners = models.IntegerField(default=1, verbose_name='Max Winners', validators=[positive, nonzero], blank=False, null=False);
  deprecated_provided = models.CharField(max_length=64,blank=True,verbose_name='*DEPRECATED* Provided By') # Deprecated
  contributors = models.ManyToManyField('Donor', related_name='prizescontributed', blank=True, null=True);
  class Meta:
    app_label = 'tracker'
    ordering = [ 'event__date', 'startrun__starttime', 'starttime', 'name' ]
    unique_together = ( 'name', 'event' )
  def natural_key(self):
    return (self.name, self.event.natural_key())
  def __unicode__(self):
    return unicode(self.name)
  def clean(self):

    if (not self.startrun) != (not self.endrun):
      raise ValidationError('Must have both Start Run and End Run set, or neither')
    if self.startrun and self.event != self.startrun.event:
      raise ValidationError('Prize Event must be the same as Start Run Event')
    if self.endrun and self.event != self.endrun.event:
      raise ValidationError('Prize Event must be the same as End Run Event')
    if self.startrun and self.startrun.starttime > self.endrun.starttime:
      raise ValidationError('Start Run must begin sooner than End Run')
    if (not self.starttime) != (not self.endtime):
      raise ValidationError('Must have both Start Run and End Run set, or neither')
    if self.starttime and self.starttime > self.endtime:
      raise ValidationError('Prize Start Time must be later than End Time')
    if self.startrun and self.starttime:
      raise ValidationError('Cannot have both Start/End Run and Start/End Time set')
    if self.maximumbid != None and self.maximumbid < self.minimumbid:
      raise ValidationError('Maximum Bid cannot be lower than Minimum Bid')
    if not self.sumdonations and self.maximumbid != self.minimumbid:
      raise ValidationError('Maximum Bid cannot differ from Minimum Bid if Sum Donations is not checked')
  def eligible_donors(self):
    qs = Donation.objects.filter(event=self.event,transactionstate='COMPLETED').select_related('donor')
    qs = qs.exclude(donor__prizeswon__category=self.category, donor__prizeswon__event=self.event);
    if self.ticketdraw:
      qs = qs.filter(tickets__prize=self).annotate(ticketAmount=Sum('tickets__amount'));
    elif self.has_draw_time():
      qs = qs.filter(timereceived__gte=self.start_draw_time(),timereceived__lte=self.end_draw_time());
    donors = {}
    for d in qs:
      if self.sumdonations:
        donors.setdefault(d.donor, Decimal('0.0'))
        if self.ticketdraw:
          donors[d.donor] += d.ticketAmount;
        else:
          donors[d.donor] += d.amount
      else:
        if self.ticketdraw:
          donors[d.donor] = max(d.ticketAmount,donors.get(d.donor,Decimal('0.0')))
        else:
          donors[d.donor] = max(d.amount,donors.get(d.donor,Decimal('0.0')))
    if not donors:
      return []
    elif self.randomdraw:
      def weight(mn,mx,a):
        if a < mn: return 0.0
        if mx != None and a > mx: return float(mx/mn)
        return float(a/mn)
      return sorted(filter(lambda d: d['weight'] >= 1.0,map(lambda d: {'donor':d[0].id,'amount':d[1],'weight':weight(self.minimumbid,self.maximumbid,d[1])}, donors.items())),key=lambda d: d['donor'])
    else:
      m = max(donors.items(), key=lambda d: d[1])
      return [{'donor':m[0].id,'amount':m[1],'weight':1.0}]
  def games_based_drawing(self):
    return self.startrun and self.endrun;
  def games_range(self):
    if self.games_based_drawing():
      return SpeedRun.objects.filter(event=self.event, starttime__gte=self.startrun.starttime, endtime__lte=self.endrun.endtime);
    else:
      return SpeedRun.objects.none();
  def has_draw_time(self):
    return self.start_draw_time() and self.end_draw_time();
  def start_draw_time(self):
    if self.startrun:
      return self.startrun.starttime.replace(tzinfo=pytz.utc);
    elif self.starttime:
      return self.starttime.replace(tzinfo=pytz.utc);
    else:
      return None;
  def end_draw_time(self):
    if self.endrun:
      return self.endrun.endtime.replace(tzinfo=pytz.utc);
    elif self.endtime:
      return self.endtime.replace(tzinfo=pytz.utc);
    else:
      return None;
  def maxed_winners(self):
    return self.maxwinners == self.winners.count();
  def get_winner(self):
    if self.maxwinners == 1:
      if self.winners.exists():
        return self.winners.all()[0];
      else:
        return None;
    else:
      raise Exception("Cannot get single winner for multi-winner prize");

class PrizeTicket(models.Model):
  prize = models.ForeignKey('Prize',related_name='tickets');
  donation = models.ForeignKey('Donation', related_name='tickets');
  amount = models.DecimalField(decimal_places=2,max_digits=20,validators=[positive,nonzero]);
  class Meta:
    app_label = 'tracker'
    verbose_name = 'Prize Ticket';
    ordering = [ '-donation__timereceived' ];
  def clean(self):
    self.donation.clean(self);
  def __unicode__(self):
    return unicode(self.prize) + ' -- ' + unicode(self.donation);

class PrizeWinner(models.Model):
  winner = models.ForeignKey('Donor', null=False, blank=False);
  prize = models.ForeignKey('Prize', null=False, blank=False);
  emailsent = models.BooleanField(default=False, verbose_name='Email Sent');
  class Meta:
    app_label = 'tracker'
    unique_together = ( 'prize', 'winner', );
  def validate_unique(self, **kwargs):
    if 'winner' not in kwargs and 'prize' not in kwargs and self.prize.category != None:
      for prizeWon in PrizeWinner.objects.filter(prize__category=self.prize.category, winner=self.winner, prize__event=self.prize.event):
        if prizeWon.id != self.id:
          raise ValidationError('Category, winner, and prize must be unique together');

class PrizeCategoryManager(models.Manager):
  def get_by_natural_key(self, name):
    return self.get(name=name)

class PrizeCategory(models.Model):
  objects = PrizeCategoryManager()
  name = models.CharField(max_length=64,unique=True)
  class Meta:
    app_label = 'tracker'
    verbose_name = 'Prize Category'
    verbose_name_plural = 'Prize Categories'
  def natural_key(self):
    return (self.name,)
  def __unicode__(self):
    return self.name

