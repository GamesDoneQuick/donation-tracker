from datetime import datetime
from decimal import Decimal
from gettext import gettext as _

import mptt.models
import pytz
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import signals, Sum, Q
from django.dispatch import receiver
from django.urls import reverse

from tracker.validators import positive, nonzero

__all__ = [
    'Bid',
    'DonationBid',
    'BidSuggestion',
]


class BidManager(models.Manager):
    def get_by_natural_key(self, event, name, speedrun=None, parent=None):
        from .event import Event, SpeedRun

        return self.get(
            event=Event.objects.get_by_natural_key(*event),
            name=name,
            speedrun=SpeedRun.objects.get_by_natural_key(*speedrun)
            if speedrun
            else None,
            parent=self.get_by_natural_key(*parent) if parent else None,
        )


class Bid(mptt.models.MPTTModel):
    objects = BidManager()
    event = models.ForeignKey(
        'Event',
        on_delete=models.PROTECT,
        verbose_name='Event',
        null=True,
        blank=True,
        related_name='bids',
        help_text='Required for top level bids if Run is not set',
    )
    speedrun = models.ForeignKey(
        'SpeedRun',
        on_delete=models.PROTECT,
        verbose_name='Run',
        null=True,
        blank=True,
        related_name='bids',
    )
    parent = mptt.models.TreeForeignKey(
        'self',
        on_delete=models.PROTECT,
        verbose_name='Parent',
        editable=False,
        null=True,
        blank=True,
        related_name='options',
    )
    name = models.CharField(max_length=64)
    state = models.CharField(
        max_length=32,
        db_index=True,
        default='OPENED',
        choices=(
            ('PENDING', 'Pending'),
            ('DENIED', 'Denied'),
            ('HIDDEN', 'Hidden'),
            ('OPENED', 'Opened'),
            ('CLOSED', 'Closed'),
        ),
    )
    description = models.TextField(max_length=1024, blank=True)
    shortdescription = models.TextField(
        max_length=256,
        blank=True,
        verbose_name='Short Description',
        help_text='Alternative description text to display in tight spaces',
    )
    goal = models.DecimalField(
        decimal_places=2, max_digits=20, null=True, blank=True, default=None
    )
    istarget = models.BooleanField(
        default=False,
        verbose_name='Target',
        help_text="Set this if this bid is a 'target' for donations (bottom level choice or challenge)",
    )
    allowuseroptions = models.BooleanField(
        default=False,
        verbose_name='Allow User Options',
        help_text='If set, this will allow donors to specify their own options on the donate page (pending moderator approval)',
    )
    option_max_length = models.PositiveSmallIntegerField(
        'Max length of user suggestions',
        blank=True,
        null=True,
        default=None,
        validators=[MinValueValidator(1), MaxValueValidator(64)],
        help_text='If allowuseroptions is set, this sets the maximum length of user-submitted bid suggestions',
    )
    revealedtime = models.DateTimeField(
        verbose_name='Revealed Time', null=True, blank=True
    )
    biddependency = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        verbose_name='Dependency',
        null=True,
        blank=True,
        related_name='dependent_bids',
    )
    total = models.DecimalField(
        decimal_places=2, max_digits=20, editable=False, default=Decimal('0.00')
    )
    count = models.IntegerField(editable=False)

    class Meta:
        app_label = 'tracker'
        unique_together = (('event', 'name', 'speedrun', 'parent',),)
        ordering = ['event__datetime', 'speedrun__starttime', 'parent__name', 'name']
        permissions = (
            ('top_level_bid', 'Can create new top level bids'),
            ('delete_all_bids', 'Can delete bids with donations attached'),
            ('view_hidden', 'Can view hidden bids'),
        )

    class MPTTMeta:
        order_insertion_by = ['name']

    def get_absolute_url(self):
        return reverse('tracker:bid', args=(self.id,))

    def natural_key(self):
        if self.parent:
            return (
                self.event.natural_key(),
                self.name,
                self.speedrun.natural_key() if self.speedrun else None,
                self.parent.natural_key(),
            )
        elif self.speedrun:
            return (self.event.natural_key(), self.name, self.speedrun.natural_key())
        else:
            return (self.event.natural_key(), self.name)

    def clean(self):
        # Manually de-normalize speedrun/event/state to help with searching
        # TODO: refactor this logic, it should be correct, but is probably not minimal

        if self.option_max_length:
            if not self.allowuseroptions:
                raise ValidationError(
                    {
                        'option_max_length': ValidationError(
                            _('Cannot set option_max_length without allowuseroptions'),
                            code='invalid',
                        ),
                    }
                )
            if self.id:
                for child in self.get_children():
                    if len(child.name) > self.option_max_length:
                        raise ValidationError(
                            _(
                                'Cannot set option_max_length to %(length)d, child name `%(name)s` is too long'
                            ),
                            code='invalid',
                            params={
                                'length': self.option_max_length,
                                'name': child.name,
                            },
                        )
                        # TODO: why is this printing 'please enter a whole number'?
                        # raise ValidationError({
                        #     'option_max_length': ValidationError(
                        #         _('Cannot set option_max_length to %(length), child name %(name) is too long'),
                        #         code='invalid',
                        #         params={
                        #             'length': self.option_max_length,
                        #             'name': child.name,
                        #         }
                        #     ),
                        # })

        # TODO: move this to save/a post_save signal?
        if self.speedrun:
            self.event = self.speedrun.event
        # TODO: move some of this to save/a post_save signal?
        if self.parent:
            curr = self.parent
            while curr.parent is not None:
                curr = curr.parent
            root = curr
            self.speedrun = root.speedrun
            self.event = root.event
            if self.state not in ['PENDING', 'DENIED', 'HIDDEN']:
                self.state = root.state
            max_len = self.parent.option_max_length
            if max_len and len(self.name) > max_len:
                raise ValidationError(
                    {
                        'name': ValidationError(
                            _('Name is longer than %(limit)s characters'),
                            params={'limit': max_len},
                            code='invalid',
                        ),
                    }
                )
        # TODO: move this to save/a post_save signal?
        if self.biddependency:
            if self.parent or self.speedrun:
                if self.event != self.biddependency.event:
                    raise ValidationError('Dependent bids must be on the same event')
            self.event = self.biddependency.event
            if not self.speedrun:
                self.speedrun = self.biddependency.speedrun
        if not self.parent:
            if not self.get_event():
                raise ValidationError('Top level bids must have their event set')
        # TODO: move this to save/a post_save signal?
        if self.id:
            for option in self.get_descendants():
                option.speedrun = self.speedrun
                option.event = self.event
                if option.state not in ['PENDING', 'DENIED', 'HIDDEN']:
                    option.state = self.state
                option.save()
        if not self.goal:
            self.goal = None
        elif self.goal <= Decimal('0.0'):
            raise ValidationError('Goal should be a positive value')
        if self.istarget and self.options.count() != 0:
            raise ValidationError('Targets cannot have children')
        if self.parent and self.parent.istarget:
            raise ValidationError('Cannot set that parent, parent is a target')
        if self.istarget and self.allowuseroptions:
            raise ValidationError(
                'A bid target cannot allow user options, since it cannot have children.'
            )
        same_name = Bid.objects.filter(
            speedrun=self.speedrun,
            event=self.event,
            parent=self.parent,
            name__iexact=self.name,
        ).exclude(pk=self.pk)
        if same_name.exists():
            raise ValidationError(
                'Cannot have a bid under the same event/run/parent with the same name'
            )
        # TODO: move this to save/a post_save signal?
        if self.state in ['OPENED', 'CLOSED'] and not self.revealedtime:
            self.revealedtime = datetime.utcnow().replace(tzinfo=pytz.utc)
        self.update_total()

    @property
    def has_options(self):
        return self.allowuseroptions or self.public_options.exists()

    @property
    def public_options(self):
        return self.options.filter(Q(state='OPENED') | Q(state='CLOSED')).order_by(
            '-total'
        )

    def update_total(self):
        if self.istarget:
            self.total = self.bids.filter(
                donation__transactionstate='COMPLETED'
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
            self.count = self.bids.filter(
                donation__transactionstate='COMPLETED'
            ).count()
            # auto close this if it's a challenge with no children and the goal's been met
            if (
                self.goal
                and self.state == 'OPENED'
                and self.total >= self.goal
                and self.istarget
            ):
                self.state = 'CLOSED'
        else:
            options = self.options.exclude(
                state__in=('HIDDEN', 'DENIED', 'PENDING')
            ).aggregate(Sum('total'), Sum('count'))
            self.total = options['total__sum'] or Decimal('0.00')
            self.count = options['count__sum'] or 0

    def get_event(self):
        if self.speedrun:
            return self.speedrun.event
        else:
            return self.event

    def full_label(self, addMoney=True):
        result = [self.fullname()]
        if self.speedrun:
            result = [self.speedrun.name_with_category(), ' : '] + result
        if addMoney:
            result += [' $', '%0.2f' % self.total]
            if self.goal:
                result += [' / ', '%0.2f' % self.goal]
        return ''.join(result)

    def __str__(self):
        if self.parent:
            return f'{self.parent} (Parent) -- {self.name}'
        elif self.speedrun:
            return f'{self.speedrun.name_with_category()} (Run) -- {self.name}'
        else:
            return f'{self.event} (Event) -- {self.name}'

    def fullname(self):
        parent = self.parent.fullname() + ' -- ' if self.parent else ''
        return parent + self.name


@receiver(signals.pre_save, sender=Bid)
def BidTotalUpdate(sender, instance, raw, **kwargs):
    if raw:
        return
    instance.update_total()


@receiver(signals.post_save, sender=Bid)
def BidParentUpdate(sender, instance, created, raw, **kwargs):
    if created or raw:
        return
    if instance.parent:
        instance.parent.save()


class DonationBid(models.Model):
    bid = models.ForeignKey('Bid', on_delete=models.PROTECT, related_name='bids')
    donation = models.ForeignKey(
        'Donation', on_delete=models.PROTECT, related_name='bids'
    )
    amount = models.DecimalField(
        default=0, decimal_places=2, max_digits=20, validators=[positive, nonzero]
    )

    class Meta:
        app_label = 'tracker'
        verbose_name = 'Donation Bid'
        ordering = ['-donation__timereceived']
        unique_together = (('bid', 'donation'),)

    def clean(self):
        if not self.bid_id:
            return
        if not self.bid.istarget:
            raise ValidationError('Target bid must be a leaf node')
        self.donation.clean(self)
        from .. import viewutil

        bidsTree = (
            viewutil.get_tree_queryset_all(Bid, [self.bid])
            .select_related('parent')
            .prefetch_related('options')
        )
        for bid in bidsTree:
            if bid.state == 'OPENED' and bid.goal is not None and bid.goal <= bid.total:
                bid.state = 'CLOSED'
                if hasattr(bid, 'dependent_bids_set'):
                    for dependentBid in bid.dependent_bids_set():
                        if dependentBid.state == 'HIDDEN':
                            dependentBid.state = 'OPENED'
                            dependentBid.save()

    @property
    def speedrun(self):
        return self.bid.speedrun

    @property
    def speedrun_id(self):
        return self.bid.speedrun_id

    @property
    def event(self):
        return self.bid.event

    @property
    def event_id(self):
        return self.bid.event_id

    @property
    def donor_cache(self):
        return self.donation.donor_cache

    @property
    def fullname(self):
        return self.bid.fullname()

    def __str__(self):
        return str(self.bid) + ' -- ' + str(self.donation)


@receiver(signals.post_save, sender=DonationBid)
def DonationBidParentUpdate(sender, instance, created, raw, **kwargs):
    if raw:
        return
    if instance.donation.transactionstate == 'COMPLETED':
        instance.bid.save()


# FIXME: this appears to be unused, see #154548040
class BidSuggestion(models.Model):
    bid = models.ForeignKey(
        'Bid', related_name='suggestions', null=False, on_delete=models.PROTECT
    )
    name = models.CharField(max_length=64, blank=False, null=False, verbose_name='Name')

    class Meta:
        app_label = 'tracker'
        ordering = ['name']

    def __init__(self):
        raise Exception('Nothing should be using this any more')

    def clean(self):
        sameBid = BidSuggestion.objects.filter(
            Q(name__iexact=self.name)
            & (
                Q(bid__event=self.bid.get_event())
                | Q(bid__speedrun__event=self.bid.get_event())
            )
        )
        if sameBid.exists():
            if sameBid.count() > 1 or sameBid[0].id != self.id:
                raise ValidationError(
                    'Cannot have a bid suggestion with the same name within the same event.'
                )

        # If set, limit the length of suggestions based on the parent bid's
        # setting

    def __str__(self):
        return self.name + ' -- ' + str(self.bid)
