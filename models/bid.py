from django.db import models
from django.db.models import signals,Sum
from django.core.exceptions import ValidationError
from django.dispatch import receiver

from tracker.validators import *
from tracker.models import Event,SpeedRun

from decimal import Decimal
import mptt.models;
from datetime import datetime
import pytz

__all__ = [
  'Bid',
  'DonationBid',
  'BidSuggestion',
]

class BidManager(models.Manager):
  def get_by_natural_key(self, event, name, speedrun=None, parent=None):
    return self.get(event=Event.objects.get_by_natural_key(*event),
      name=name,
      speedrun=SpeedRun.objects.get_by_natural_key(*speedrun) if speedrun else None,
      parent=self.get_by_natural_key(*parent) if parent else None)

class Bid(mptt.models.MPTTModel):
  objects = BidManager()
  event = models.ForeignKey('Event', verbose_name='Event', null=True, blank=True, related_name='bids', help_text='Required for top level bids if Run is not set');
  speedrun = models.ForeignKey('SpeedRun', verbose_name='Run', null=True, blank=True, related_name='bids');
  parent = mptt.models.TreeForeignKey('self', verbose_name='Parent', editable=False, null=True, blank=True, related_name='options');
  name = models.CharField(max_length=64);
  state = models.CharField(max_length=32,choices=(('HIDDEN', 'Hidden'), ('OPENED','Opened'), ('CLOSED','Closed')),default='OPENED');
  description = models.TextField(max_length=1024,blank=True);
  goal = models.DecimalField(decimal_places=2,max_digits=20,null=True,blank=True,default=None);
  istarget = models.BooleanField(default=False,verbose_name='Target',help_text="Set this if this bid is a 'target' for donations (bottom level choice or challenge)");
  revealedtime = models.DateTimeField(verbose_name='Revealed Time', null=True, blank=True);
  biddependency = models.ForeignKey('self', verbose_name='Dependency', null=True, blank=True, related_name='depedent_bids');
  #suggestions = models.BooleanField(default=False,help_text="Set to true for bids that are open to new suggestions, such as filenames")
  total = models.DecimalField(decimal_places=2,max_digits=20,editable=False,default=Decimal('0.00'))
  count = models.IntegerField(editable=False)
  class Meta:
    app_label = 'tracker'
    unique_together = (('event', 'name', 'speedrun', 'parent',),);
    ordering = ['event__date', 'speedrun__starttime', 'parent__name', 'name'];
    permissions = (
      ('top_level_bid', 'Can create new top level bids'),
      ('delete_all_bids', 'Can delete bids with donations attached'),
      ('view_hidden', 'Can view hidden bids'),
    )
  class MPTTMeta:
    order_insertion_by = ['name']
  def natural_key(self):
    if self.parent:
	  return (self.event.natural_key(), self.name, self.speedrun.natural_key() if self.speedrun else None, self.parent.natural_key())
    elif self.speedrun:
      return (self.event.natural_key(), self.name, self.speedrun.natural_key())
    else:
      return (self.event.natural_key(), self.name)
  def clean(self):
    # Manually de-normalize speedrun/event/state to help with searching
    if self.speedrun:
      self.event = self.speedrun.event
    if self.parent:
      curr = self.parent;
      while curr.parent != None:
        curr = curr.parent;
      root = curr;
      self.speedrun = root.speedrun;
      self.event = root.event;
      self.state = root.state;
    else:
      if not self.get_event():
        raise ValidationError('Top level bids must have their event set')
      for option in self.get_descendants():
        option.speedrun = self.speedrun;
        option.event = self.event;
        option.state = self.state;
        option.save();
    if not self.goal:
      self.goal = None;
    elif self.goal <= Decimal('0.0'):
      raise ValidationError('Goal should be a positive value');
    if self.istarget and self.options.count() != 0:
      raise ValidationError('Targets cannot have children')
    if self.parent and self.parent.istarget:
      raise ValidationError('Cannot set that parent, parent is a target')
    sameName = Bid.objects.filter(speedrun=self.speedrun, event=self.event, parent=self.parent, name__iexact=self.name);
    if sameName.exists():
      if sameName.count() > 1 or sameName[0].id != self.id:
        raise ValidationError('Cannot have a bid under the same event/run/parent with the same name');
    if self.id == None or (sameName.exists() and sameName[0].state == 'HIDDEN' and self.state == 'OPENED'):
      self.revealedtime = datetime.utcnow().replace(tzinfo=pytz.utc);
    self.update_total()

  def update_total(self):
    if self.istarget:
      self.total = self.bids.filter(donation__transactionstate='COMPLETED').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
      self.count = self.bids.filter(donation__transactionstate='COMPLETED').count()
      # auto close this if it's a challenge with no children and the goal's been met
      if self.goal and self.state == 'OPENED' and self.total >= self.goal and self.istarget:
        self.state = 'CLOSED'
    else:
      self.total = self.options.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
      self.count = self.options.aggregate(Sum('count'))['count__sum'] or 0

  def get_event(self):
    if self.speedrun:
      return self.speedrun.event;
    else:
      return self.event;

  def __unicode__(self):
    if self.parent:
      return unicode(self.parent) + ' -- ' + self.name;
    elif self.speedrun:
      return self.speedrun.name  + ' -- ' + self.name;
    else:
      return unicode(self.event) + ' -- ' + self.name;
  def fullname(self):
    return ((self.parent.fullname() + ' -- ') if self.parent else '') + self.name;

@receiver(signals.pre_save, sender=Bid)
def BidTotalUpdate(sender, instance, raw, **kwargs):
  if raw: return
  instance.update_total()

@receiver(signals.post_save, sender=Bid)
def BidParentUpdate(sender, instance, created, raw, **kwargs):
  if created or raw: return
  if instance.parent:
    instance.parent.save()

class DonationBid(models.Model):
  bid = models.ForeignKey('Bid',related_name='bids')
  donation = models.ForeignKey('Donation', related_name='bids')
  amount = models.DecimalField(decimal_places=2,max_digits=20,validators=[positive,nonzero])
  class Meta:
    app_label = 'tracker'
    verbose_name = 'Donation Bid'
    ordering = [ '-donation__timereceived' ]
  def clean(self):
    if not self.bid.is_leaf_node():
      raise ValidationError('Target bid must be a leaf node');
    self.donation.clean(self);
    import tracker.viewutil as viewutil;
    bidsTree = viewutil.get_tree_queryset_all(Bid, [self.bid]).select_related('parent').prefetch_related('options');
    bidsTree = bidsTree.annotate(**viewutil.ModelAnnotations['bid']);
    bidsMap = viewutil.FixupBidAnnotations(bidsTree);
    for bid in bidsMap.values():
      if bid.state == 'OPENED' and bid.goal != None and bid.goal <= bid.amount:
        bid.state = 'CLOSED';
        for dependentBid in bid.dependent_bids_set():
          if dependentBid.state == 'HIDDEN':
            dependentBid.state = 'OPENED';
            dependentBid.save();
  def __unicode__(self):
    return unicode(self.bid) + ' -- ' + unicode(self.donation)

@receiver(signals.post_save, sender=DonationBid)
def DonationBidParentUpdate(sender, instance, created, raw, **kwargs):
  if raw: return
  if instance.donation.transactionstate == 'COMPLETED': instance.bid.save()

class BidSuggestion(models.Model):
  bid = models.ForeignKey('Bid', related_name='suggestions', null=False);
  name = models.CharField(max_length=64, blank=False, null=False, verbose_name="Name");
  class Meta:
    app_label = 'tracker'
    ordering = [ 'name' ];
  def clean(self):
    sameBid = BidSuggestion.objects.filter(Q(name__iexact=self.name) & (Q(bid__event=self.bid.get_event()) | Q(bid__speedrun__event=self.bid.get_event())));
    if sameBid.exists():
      if sameBid.count() > 1 or sameBid[0].id != self.id:
        raise ValidationError("Cannot have a bid suggestion with the same name within the same event.");
  def __unicode__(self):
    return self.name + " -- " + unicode(self.bid);

