import logging
from datetime import datetime
from decimal import Decimal
from gettext import gettext as _

import mptt.models
import pytz
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, Sum, signals
from django.dispatch import receiver
from django.urls import reverse

from tracker.analytics import AnalyticsEventTypes, analytics
from tracker.validators import nonzero, positive

__all__ = [
    'Bid',
    'DonationBid',
    'BidSuggestion',
]

logger = logging.getLogger(__name__)


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
    repeat = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        null=True,
        blank=True,
        default=None,
        help_text='Informational field for repeated challenges, must be a divisor of goal',
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
    pinned = models.BooleanField(
        default=False, help_text='Will always show up in the current feeds'
    )

    class Meta:
        app_label = 'tracker'
        unique_together = (
            (
                'event',
                'name',
                'speedrun',
                'parent',
            ),
        )
        ordering = ['event__datetime', 'speedrun__starttime', 'parent__name', 'name']
        permissions = (
            ('top_level_bid', 'Can create new top level bids'),
            ('delete_all_bids', 'Can delete bids with donations attached'),
            ('view_hidden_bid', 'Can view hidden bids'),
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
                    _('Cannot set option_max_length without allowuseroptions'),
                    code='invalid',
                )
                # FIXME: why is this printing 'please enter a whole number'?
                # raise ValidationError(
                #     {
                #         'option_max_length': ValidationError(
                #             _('Cannot set option_max_length without allowuseroptions'),
                #             code='invalid',
                #         ),
                #     }
                # )
            if self.pk:
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

        if self.parent:
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
        if self.biddependency:
            if self.parent or self.speedrun:
                if self.event != self.biddependency.event:
                    raise ValidationError('Dependent bids must be on the same event')
        if not self.parent:
            if not self.get_event():
                raise ValidationError('Top level bids must have their event set')
        if not self.goal:
            self.goal = None
        elif self.goal <= Decimal('0.0'):
            raise ValidationError('Goal should be a positive value')
        if self.state in ['PENDING', 'DENIED'] and (
            not self.istarget or not self.parent or not self.parent.allowuseroptions
        ):
            raise ValidationError(
                {
                    'state': f'State `{self.state}` can only be set on targets with parents that allow user options'
                }
            )
        if self.pk and self.istarget and self.options.count() != 0:
            raise ValidationError('Targets cannot have children')
        if self.parent and self.parent.istarget:
            raise ValidationError('Cannot set that parent, parent is a target')
        if self.istarget and self.allowuseroptions:
            raise ValidationError(
                'A bid target cannot allow user options, since it cannot have children.'
            )
        if (
            not self.allowuseroptions
            and self.pk
            and self.get_children().filter(state__in=['PENDING', 'DENIED'])
        ):
            raise ValidationError(
                {
                    'allowuseroptions': 'Bid has pending/denied children, cannot remove allowing user options'
                }
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
        if not self.repeat:
            self.repeat = None
        elif self.repeat <= Decimal('0.0'):
            raise ValidationError({'repeat': 'Repeat should be a positive value'})
        if self.repeat:
            if not self.istarget:
                raise ValidationError({'repeat': 'Cannot set repeat on non-targets'})
            if self.parent:
                raise ValidationError({'repeat': 'Cannot set repeat on child bids'})
            if self.goal is None:
                raise ValidationError({'repeat': 'Cannot set repeat with no goal'})
            if self.goal % self.repeat != 0:
                raise ValidationError({'repeat': 'Goal must be a multiple of repeat'})

    def save(self, *args, skip_parent=False, **kwargs):
        if self.parent:
            self.check_parent()
        if self.speedrun:
            self.event = self.speedrun.event
        if self.state in ['OPENED', 'CLOSED'] and not self.revealedtime:
            self.revealedtime = datetime.utcnow().replace(tzinfo=pytz.utc)
            analytics.track(
                AnalyticsEventTypes.INCENTIVE_OPENED,
                {
                    'timestamp': self.revealedtime,
                    'bid_id': self.id,
                    'event_id': self.event_id,
                    'run_id': self.speedrun_id,
                    'parent_id': self.parent_id,
                    'name': self.name,
                    'goal': self.goal,
                    'is_target': self.istarget,
                    'allow_user_options': self.allowuseroptions,
                    'max_option_length': self.option_max_length,
                    'dependent_on_id': self.biddependency,
                },
            )
        if self.biddependency:
            self.event = self.biddependency.event
            if not self.speedrun:
                self.speedrun = self.biddependency.speedrun
        self.update_total()
        super(Bid, self).save(*args, **kwargs)
        if self.pk:
            for option in self.get_children():
                if option.check_parent():
                    option.save(skip_parent=True)
        if self.parent and not skip_parent:
            self.parent.save()

    def check_parent(self):
        changed = False
        if self.speedrun != self.parent.speedrun:
            self.speedrun = self.parent.speedrun
            changed = True
        if self.event != self.parent.event:
            self.event = self.parent.event
            changed = True
        if self.state not in ['PENDING', 'DENIED'] and self.state != self.parent.state:
            self.state = self.parent.state
            changed = True
        if self.pinned != self.parent.pinned:
            self.pinned = self.parent.pinned
            changed = True
        return changed

    @property
    def has_options(self):
        return self.allowuseroptions or self.public_options.exists()

    @property
    def public_options(self):
        return self.options.filter(Q(state='OPENED') | Q(state='CLOSED')).order_by(
            '-total'
        )

    def update_total(self):
        if not self.pk:
            self.total = 0
            self.count = 0
        elif self.istarget:
            self.total = self.bids.filter(
                donation__transactionstate='COMPLETED'
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
            self.count = self.bids.filter(
                donation__transactionstate='COMPLETED'
            ).count()
            # auto close and unpin this if it's a challenge with no children and the goal's been met
            if (
                self.goal
                and self.state == 'OPENED'
                and self.total >= self.goal
                and self.istarget
            ):
                self.state = 'CLOSED'
                self.pinned = False
                analytics.track(
                    AnalyticsEventTypes.INCENTIVE_MET,
                    {
                        'timestamp': datetime.utcnow(),
                        'bid_id': self.pk,
                        'event_id': self.event_id,
                        'run_id': self.speedrun_id,
                        'parent_id': self.parent_id,
                        'name': self.name,
                        'goal': self.goal,
                        'is_target': self.istarget,
                        'total_raised': self.total,
                        'unique_donations': self.count,
                        'allow_user_options': self.allowuseroptions,
                        'max_option_length': self.option_max_length,
                        'dependent_on_id': self.biddependency,
                    },
                )
        else:
            options = self.options.exclude(state__in=('DENIED', 'PENDING')).aggregate(
                Sum('total'), Sum('count')
            )
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
        if self.donation.event != self.bid.event:
            raise ValidationError(
                'Target bid and target donation must be part of the same event'
            )
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

    def save(self, *args, **kwargs):
        is_creating = self.pk is None
        super(DonationBid, self).save(*args, **kwargs)
        # TODO: This should move to `donateviews.process_form` to track bids that
        # are created as part of the original donation, and a separate admin view
        # to track bids applied manually by a donation processor.
        if is_creating:
            analytics.track(
                AnalyticsEventTypes.BID_APPLIED,
                {
                    'timestamp': datetime.utcnow(),
                    'event_id': self.donation.event_id,
                    'incentive_id': self.bid.id,
                    'parent_id': self.bid.parent_id,
                    'donation_id': self.donation_id,
                    'amount': self.amount,
                    'total_donation_amount': self.donation.amount,
                    'incentive_goal_amount': self.bid.goal,
                    'incentive_current_amount': self.bid.total,
                    # TODO: Set this to an actual value when tracking moves
                    # to the separate view functions.
                    'added_manually': False,
                },
            )

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
    def timereceived(self):
        return self.donation.timereceived

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
