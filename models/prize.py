from decimal import Decimal

import pytz

from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Sum, Q
from django.contrib.auth.models import User

from ..validators import *
from .event import LatestEvent
from ..models import Event, Donation, SpeedRun
import settings

__all__ = [
  'Prize',
  'PrizeTicket',
  'PrizeWinner',
  'PrizeCategory',
  'DonorPrizeEntry',
]

USER_MODEL_NAME = getattr(settings, 'AUTH_USER_MODEL', User)

class PrizeManager(models.Manager):
  def get_by_natural_key(self, name, event):
    return self.get(name=name,event=Event.objects.get_by_natural_key(*event))


class Prize(models.Model):
  objects = PrizeManager()
  name = models.CharField(max_length=64)
  category = models.ForeignKey('PrizeCategory', on_delete=models.PROTECT, null=True,blank=True)
  image = models.URLField(max_length=1024,null=True,blank=True)
  altimage = models.URLField(max_length=1024,null=True,blank=True,verbose_name='Alternate Image',help_text='A second image to display in situations where the default image is not appropriate (tight spaces, stream, etc...)')
  imagefile = models.FileField(upload_to='prizes',null=True,blank=True)
  description = models.TextField(max_length=1024,null=True,blank=True)
  shortdescription = models.TextField(max_length=256,blank=True,verbose_name='Short Description',help_text="Alternative description text to display in tight spaces")
  extrainfo = models.TextField(max_length=1024,null=True,blank=True)
  estimatedvalue = models.DecimalField(decimal_places=2,max_digits=20,null=True,blank=True,verbose_name='Estimated Value',validators=[positive,nonzero])
  minimumbid = models.DecimalField(decimal_places=2,max_digits=20,default=Decimal('5.0'),verbose_name='Minimum Bid',validators=[positive,nonzero])
  maximumbid = models.DecimalField(decimal_places=2,max_digits=20,null=True,blank=True,default=Decimal('5.0'),verbose_name='Maximum Bid',validators=[positive,nonzero])
  sumdonations = models.BooleanField(default=False,verbose_name='Sum Donations')
  randomdraw = models.BooleanField(default=True,verbose_name='Random Draw')
  ticketdraw = models.BooleanField(default=False,verbose_name='Ticket Draw')
  event = models.ForeignKey('Event',on_delete=models.PROTECT,default=LatestEvent)
  startrun = models.ForeignKey('SpeedRun',on_delete=models.PROTECT,related_name='prize_start',null=True,blank=True,verbose_name='Start Run')
  endrun = models.ForeignKey('SpeedRun',on_delete=models.PROTECT,related_name='prize_end',null=True,blank=True,verbose_name='End Run')
  starttime = models.DateTimeField(null=True,blank=True,verbose_name='Start Time')
  endtime = models.DateTimeField(null=True,blank=True,verbose_name='End Time')
  maxwinners = models.IntegerField(default=1, verbose_name='Max Winners', validators=[positive, nonzero], blank=False, null=False)
  maxmultiwin = models.IntegerField(default=1, verbose_name='Max Wins per Donor', validators=[positive, nonzero], blank=False, null=False)
  #provided = models.CharField(max_length=64,blank=True, null=True, verbose_name='Provided By')
  #provideremail = models.EmailField(max_length=128, blank=True, null=True, verbose_name='Provider Email')
  provider = models.ForeignKey(USER_MODEL_NAME, null=True)
  acceptemailsent = models.BooleanField(default=False, verbose_name='Accept/Deny Email Sent')
  creator = models.CharField(max_length=64, blank=True, null=True, verbose_name='Creator')
  creatoremail = models.EmailField(max_length=128, blank=True, null=True, verbose_name='Creator Email')
  creatorwebsite = models.CharField(max_length=128, blank=True, null=True, verbose_name='Creator Website')
  state = models.CharField(max_length=32,choices=(('PENDING', 'Pending'), ('ACCEPTED','Accepted'), ('DENIED', 'Denied'), ('FLAGGED','Flagged')),default='PENDING')

  class Meta:
    app_label = 'tracker'
    ordering = [ 'event__date', 'startrun__starttime', 'starttime', 'name' ]
    unique_together = ( 'name', 'event' )

  def natural_key(self):
    return (self.name, self.event.natural_key())

  def __unicode__(self):
    return unicode(self.name)

  def clean(self, winner=None):
    if self.maxmultiwin > 1 and self.category != None:
      raise ValidationError('A donor may not win more than one prize of any category, so setting a prize to have multiple wins per single donor with a non-null category is incompatible.')
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
    if self.randomdraw:
      if self.maximumbid != None and self.maximumbid < self.minimumbid:
        raise ValidationError('Maximum Bid cannot be lower than Minimum Bid')
      if not self.sumdonations and self.maximumbid != self.minimumbid:
        raise ValidationError('Maximum Bid cannot differ from Minimum Bid if Sum Donations is not checked')
    if self.image and self.imagefile:
      raise ValidationError('Cannot have both an Image URL and an Image File')

  def eligible_donors(self):
    donationSet = Donation.objects.filter(event=self.event,transactionstate='COMPLETED').select_related('donor')
    # remove all donations from donors who have already won this prize, or have won a prize under the same category for this event
    if self.category != None:
      donationSet = donationSet.exclude(Q(donor__prizewinner__prize__category=self.category, donor__prizewinner__prize__event=self.event))
    fullDonors = PrizeWinner.objects.filter(prize=self,sumcount=self.maxmultiwin)
    donationSet = donationSet.exclude(donor__in=map(lambda x: x.winner, fullDonors))
    if self.ticketdraw:
      donationSet = donationSet.filter(tickets__prize=self)
    elif self.has_draw_time():
      donationSet = donationSet.filter(timereceived__gte=self.start_draw_time(),timereceived__lte=self.end_draw_time())
    donors = {}
    for donation in donationSet:
      if self.sumdonations:
        donors.setdefault(donation.donor, Decimal('0.0'))
        if self.ticketdraw:
          donors[donation.donor] += donation.prize_ticket_amount(self)
        else:
          donors[donation.donor] += donation.amount
      else:
        if self.ticketdraw:
          donors[donation.donor] = max(donation.prize_ticket_amount(self),donors.get(donation.donor,Decimal('0.0')))
        else:
          donors[donation.donor] = max(donation.amount,donors.get(donation.donor,Decimal('0.0')))
    directEntries = DonorPrizeEntry.objects.filter(prize=self).exclude(Q(donor__in=map(lambda x: x.winner, fullDonors)))
    for entry in directEntries:
      donors.setdefault(entry.donor, Decimal('0.0'))
      donors[entry.donor] = max(entry.weight*self.minimumbid, donors[entry.donor])
      if self.maximumbid:
        donors[entry.donor] = min(donors[entry.donor], self.maximumbid)
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
    return self.startrun and self.endrun

  def games_range(self):
    if self.games_based_drawing():
      return SpeedRun.objects.filter(event=self.event, starttime__gte=self.startrun.starttime, endtime__lte=self.endrun.endtime)
    else:
      return SpeedRun.objects.none()

  def has_draw_time(self):
    return self.start_draw_time() and self.end_draw_time()

  def start_draw_time(self):
    if self.startrun:
      return self.startrun.starttime.replace(tzinfo=pytz.utc)
    elif self.starttime:
      return self.starttime.replace(tzinfo=pytz.utc)
    else:
      return None

  def end_draw_time(self):
    if self.endrun:
      return self.endrun.endtime.replace(tzinfo=pytz.utc)
    elif self.endtime:
      return self.endtime.replace(tzinfo=pytz.utc)
    else:
      return None

  def contains_draw_time(self, time):
    return not self.has_draw_time() or (self.start_draw_time() <= time and self.end_draw_time() >= time)

  def current_win_count(self):
    return sum(filter(lambda x: x != None, self.get_prize_winners().aggregate(Sum('pendingcount'),Sum('acceptcount')).values()))

  def maxed_winners(self):
    return self.current_win_count() == self.maxwinners

  def get_prize_winners(self):
    return self.prizewinner_set.filter(Q(acceptcount__gte=1) | Q(pendingcount__gte=1))

  def get_prize_winner(self):
    if self.maxwinners == 1:
      winners = self.get_prize_winners()
      if len(winners) > 0:
        return winners[0]
      else:
        return None
    else:
      raise Exception("Cannot get single winner for multi-winner prize")

  def get_winners(self):
    return list(map(lambda x: x.winner, self.get_prize_winners()))

  def get_winner(self):
    prizeWinner = self.get_prize_winner()
    if prizeWinner:
      return prizeWinner.winner
    else:
      return None


class PrizeTicket(models.Model):
  prize = models.ForeignKey('Prize', on_delete=models.PROTECT, related_name='tickets')
  donation = models.ForeignKey('Donation', on_delete=models.PROTECT, related_name='tickets')
  amount = models.DecimalField(decimal_places=2,max_digits=20,validators=[positive,nonzero])
  class Meta:
    app_label = 'tracker'
    verbose_name = 'Prize Ticket'
    ordering = [ '-donation__timereceived' ]
    unique_together = ( 'prize', 'donation' )

  def clean(self):
    if not self.prize.ticketdraw:
      raise ValidationError('Cannot assign tickets to non-ticket prize')
    self.donation.clean(self)

  def __unicode__(self):
    return unicode(self.prize) + ' -- ' + unicode(self.donation)


class PrizeWinner(models.Model):
  winner = models.ForeignKey('Donor', null=False, blank=False, on_delete=models.PROTECT)
  pendingcount = models.IntegerField(default=1, null=False, blank=False, validators=[positive], verbose_name='Pending Count', help_text='The number of pending wins this donor has on this prize.')
  acceptcount = models.IntegerField(default=0, null=False, blank=False, validators=[positive], verbose_name='Accept Count', help_text='The number of copied this winner has won and accepted.')
  declinecount = models.IntegerField(default=0, null=False, blank=False, validators=[positive], verbose_name='Decline Count', help_text='The number of declines this donor has put towards this prize. Set it to the max prize multi win amount to prevent this donor from being entered from future drawings.')
  sumcount = models.IntegerField(default=1, null=False, blank=False, editable=False, validators=[positive], verbose_name='Sum Counts', help_text='The total number of prize instances associated with this winner')
  prize = models.ForeignKey('Prize', null=False, blank=False, on_delete=models.PROTECT)
  emailsent = models.BooleanField(default=False, verbose_name='Notification Email Sent')
  shippingemailsent = models.BooleanField(default=False, verbose_name='Shipping Email Sent')
  trackingnumber = models.CharField(max_length=64, verbose_name='Tracking Number', blank=True, null=False)
  shippingstate = models.CharField(max_length=64, verbose_name='Shipping State', choices=(('PENDING','Pending'),('SHIPPED','Shipped')), default='PENDING')
  shippingcost = models.DecimalField(decimal_places=2,max_digits=20,null=True,blank=True,verbose_name='Shipping Cost',validators=[positive,nonzero])

  class Meta:
    app_label = 'tracker'
    verbose_name = 'Prize Winner'
    unique_together = ( 'prize', 'winner', )

  def check_multiwin(self, value):
    if value > self.prize.maxmultiwin:
      raise ValidationError('Count must not exceed the prize multi win amount ({0})'.format(self.prize.maxmultiwin))
    return value

  def clean_pendingcount(self):
    return self.check_multiwin(self.pendingcount)

  def clean_acceptcount(self):
    return self.check_multiwin(self.acceptcount)

  def clean_declinecount(self):
    return self.check_multiwin(self.declinecount)

  def clean(self):
    self.sumcount = self.pendingcount + self.acceptcount + self.declinecount
    if self.sumcount == 0:
      raise ValidationError('Sum of counts must be greater than zero')
    if self.sumcount > self.prize.maxmultiwin:
      raise ValidationError('Sum of counts must be at most the prize multi-win multiplicity')
    prizeSum = self.acceptcount + self.pendingcount
    for winner in self.prize.prizewinner_set.exclude(pk=self.pk):
      prizeSum += winner.acceptcount + winner.pendingcount
    if prizeSum > self.prize.maxwinners:
      raise ValidationError('Number of prize winners is greater than the maximum for this prize.')

  def validate_unique(self, **kwargs):
    if 'winner' not in kwargs and 'prize' not in kwargs and self.prize.category != None:
      for prizeWon in PrizeWinner.objects.filter(prize__category=self.prize.category, winner=self.winner, prize__event=self.prize.event):
        if prizeWon.id != self.id:
          raise ValidationError('Category, winner, and prize must be unique together')

  def save(self, *args,**kwargs):
    self.sumcount = self.pendingcount + self.acceptcount + self.declinecount
    super(PrizeWinner, self).save(*args, **kwargs)

  def __unicode__(self):
    return unicode(self.prize) + u' -- ' + unicode(self.winner)


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


class DonorPrizeEntry(models.Model):
  donor = models.ForeignKey('Donor', null=False, blank=False, on_delete=models.PROTECT)
  prize = models.ForeignKey('Prize', null=False, blank=False, on_delete=models.PROTECT)
  weight = models.DecimalField(decimal_places=2,max_digits=20,default=Decimal('1.0'),verbose_name='Entry Weight',validators=[positive,nonzero], help_text='This is the weight to apply this entry in the drawing (if weight is applicable).')

  class Meta:
    app_label = 'tracker'
    verbose_name = 'Donor Prize Entry'
    verbose_name_plural = 'Donor Prize Entries'
    unique_together = ('prize','donor',)

  def __unicode__(self):
    return unicode(self.donor) + ' entered to win ' + unicode(self.prize)

