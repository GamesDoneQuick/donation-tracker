import logging
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from gettext import gettext as _

import mptt.managers
import mptt.models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Count, F, Q, Sum, signals
from django.db.models.functions import Coalesce
from django.dispatch import receiver
from django.urls import reverse

from tracker import util
from tracker.analytics import AnalyticsEventTypes, analytics
from tracker.validators import nonzero, positive

from .fields import TimestampField

__all__ = [
    'Bid',
    'DonationBid',
    'BidSuggestion',
]

logger = logging.getLogger(__name__)


class BidQuerySet(mptt.managers.TreeQuerySet):
    HIDDEN_FEEDS = ('pending', 'all')
    PUBLIC_FEEDS = ('current', 'public', 'open', 'closed')
    ALL_FEEDS = HIDDEN_FEEDS + PUBLIC_FEEDS

    def upcoming(self, **kwargs):
        return self.filter(self.upcoming_filter(**kwargs))

    def upcoming_filter(self, **kwargs):
        from .event import SpeedRun

        return Q(speedrun__in=(SpeedRun.objects.upcoming(**kwargs)))

    def public(self):
        return self.filter(state__in=['OPENED', 'CLOSED'])

    def hidden(self):
        return self.filter(state__in=['HIDDEN', 'PENDING', 'DENIED'])

    def open(self):
        return self.filter(state='OPENED')

    def closed(self):
        return self.filter(state='CLOSED')

    def current(self, **kwargs):
        return self.filter(
            Q(state__in=['OPENED', 'CLOSED'])
            & (self.upcoming_filter(**kwargs) | Q(pinned=True))
        )

    def pending(self):
        # exclude anything that doesn't actually have a cleared donation
        return self.filter(state='PENDING').exclude(count=0)

    def with_annotations(self):
        return self.annotate(
            parent_name=F('parent__name'),
            speedrun_name=F('speedrun__name'),
            event_name=F('event__name'),
        ).order_by(
            *Bid._meta.ordering
        )  # Django 3.x erases the default ordering after an annotate


class BidManager(mptt.managers.TreeManager):
    def get_by_natural_key(self, event, name, speedrun, parent):
        from .event import Event, SpeedRun

        return self.get(
            event=Event.objects.get_by_natural_key(*event),
            name=name,
            speedrun=(
                SpeedRun.objects.get_by_natural_key(*speedrun) if speedrun else None
            ),
            parent=self.get_by_natural_key(*parent) if parent else None,
        )


class Bid(mptt.models.MPTTModel):
    HIDDEN_FEEDS = BidQuerySet.HIDDEN_FEEDS
    PUBLIC_FEEDS = BidQuerySet.PUBLIC_FEEDS
    ALL_FEEDS = BidQuerySet.ALL_FEEDS
    HIDDEN_STATES = ('PENDING', 'DENIED', 'HIDDEN')
    PUBLIC_STATES = ('OPENED', 'CLOSED')
    ALL_STATES = HIDDEN_STATES + PUBLIC_STATES

    objects = BidManager.from_queryset(BidQuerySet)()
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
    chain = models.BooleanField(
        default=False,
        help_text='Use for stretch goals, this requires a linear chain of single-descendants to work',
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
    chain_goal = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        editable=False,
        null=True,
        blank=True,
        default=None,
        help_text='The total goal of all preceding bids in the chain (INCLUDING this bid)',
    )
    chain_remaining = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        editable=False,
        null=True,
        blank=True,
        default=None,
        help_text='The total goal of all remaining bids in the chain (EXCLUDING this bid)',
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
    accepted_number = models.IntegerField(
        blank=True,
        null=True,
        verbose_name='Accepted Number of Options',
        help_text='Number of accepted options that will be used, e.g. top two choices for a race',
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
    estimate = TimestampField(
        null=True,
        blank=True,
        always_show_m=True,
        help_text='how much this incentive will add to run/setup time, if applicable',
    )
    close_at = models.CharField(
        null=True,
        blank=True,
        max_length=64,
        help_text='approximately how far into the run the incentive will need to be closed',
    )
    post_run = models.BooleanField(
        default=False,
        help_text='this incentive takes place after the run (part of setup time)',
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
            ('approve_bid', 'Can approve or deny pending bids'),
        )

    class MPTTMeta:
        order_insertion_by = ['name']

    def get_absolute_url(self):
        return util.build_public_url(reverse('tracker:bid', args=(self.id,)))

    def natural_key(self):
        return (
            self.event.natural_key(),
            self.name,
            self.speedrun.natural_key() if self.speedrun else None,
            self.parent.natural_key() if self.parent else None,
        )

    def clean(self):
        # Manually de-normalize speedrun/event/state to help with searching
        # TODO: refactor this logic, it should be correct, but is probably not minimal

        errors = defaultdict(list)

        if self.speedrun:
            self.event = self.speedrun.event

        if self.option_max_length:
            if not self.allowuseroptions:
                # FIXME: why is this printing 'please enter a whole number'?
                # errors['option_max_length'].append(ValidationError(
                errors['__all__'].append(
                    ValidationError(
                        _('Cannot set option_max_length without allowuseroptions'),
                    )
                )
            if self.pk:
                for child in self.get_children():
                    if len(child.name) > self.option_max_length:
                        # FIXME: why is this printing 'please enter a whole number'?
                        # errors['option_max_length'].append(ValidationError(
                        errors['__all__'].append(
                            ValidationError(
                                _(
                                    'Cannot set option_max_length to %(length)d, child name `%(name)s` is too long'
                                ),
                                params={
                                    'length': self.option_max_length,
                                    'name': child.name,
                                },
                            )
                        )

        if self.parent_id:
            root = self.parent.get_root()
            self.speedrun = root.speedrun
            self.event = root.event

            max_len = root.option_max_length
            if max_len and len(self.name) > max_len:
                errors['name'].append(
                    ValidationError(
                        _('Name is longer than %(limit)s characters'),
                        params={'limit': max_len},
                    )
                )
            if self.parent.chain:
                if self.parent.get_children().exclude(pk=self.pk).exists():
                    errors['parent'].append(
                        ValidationError(
                            _('Chained parents cannot have more than one child')
                        )
                    )
            elif self.parent.istarget:
                errors['parent'].append(
                    ValidationError(
                        _('Cannot set that parent, parent is a non-chained target')
                    )
                )
            if self.goal is not None and not (self.chain or self.parent.chain):
                errors['goal'].append(
                    ValidationError(_('Cannot set a goal in a non-chained child bid'))
                )
            if self.close_at:
                errors['close_at'].append(
                    ValidationError(_('Cannot set close time on a child bid'))
                )
            if self.accepted_number:
                errors['accepted_number'].append(
                    ValidationError(_('Accepted Number only applies to top-level bids'))
                )

        if self.biddependency:
            if self.parent or self.speedrun:
                if self.event != self.biddependency.event:
                    errors['event'].append(
                        ValidationError(_('Dependent bids must be on the same event'))
                    )

        if not self.event:
            errors['event'].append(
                ValidationError(
                    _('Bids without a parent or speedrun must have their event set')
                )
            )

        if not self.goal:
            if self.chain or (self.parent and self.parent.chain):
                errors['goal'].append(
                    ValidationError(_('Chained bids must have a goal set'))
                )
            else:
                self.goal = None
        elif self.goal <= Decimal('0.0'):
            errors['goal'].append(ValidationError(_('Goal should be a positive value')))

        if self.state in ['PENDING', 'DENIED'] and (
            not self.istarget or not self.parent or not self.parent.allowuseroptions
        ):
            errors['state'].append(
                ValidationError(
                    _(
                        'State `%(state)s` can only be set on targets with parents that allow user options'
                    ),
                    params={'state': self.state},
                )
            )

        if self.istarget:
            if self.chain:
                if self.parent:
                    errors['istarget'].append(
                        ValidationError(_('Chained children cannot be a target'))
                    )
            elif self.pk and self.options.count() != 0:
                errors['istarget'].append(
                    ValidationError(_('Targets cannot have children'))
                )
            if self.accepted_number:
                errors['accepted_number'].append(
                    ValidationError(_('Targets cannot have children'))
                )
            if self.allowuseroptions:
                errors['allowuseroptions'].append(
                    ValidationError(
                        _(
                            'Target cannot allow user options, since it cannot have children'
                        )
                    )
                )
        else:
            if self.chain and not self.parent:
                errors['istarget'].append(
                    ValidationError(_('The top of a chain must be a target.'))
                )

        if (
            not self.allowuseroptions
            and self.pk
            and self.get_children().filter(state__in=['PENDING', 'DENIED'])
        ):
            errors['allowuseroptions'].append(
                ValidationError(
                    _(
                        'Bid has pending/denied children, cannot remove allowing user options'
                    )
                )
            )

        same_name = Bid.objects.filter(
            speedrun=self.speedrun,
            event=self.event,
            # FIXME: Django 5.0 started complaining about self.parent during tests, if a child tried to clean itself
            #  before the parent was saved, but this might not ever happen in the real world, so spend some time
            #  looking into this when possible
            parent=self.parent_id,
            name__iexact=self.name,
        ).exclude(pk=self.pk)
        if same_name.exists():
            errors['name'].append(
                ValidationError(
                    _(
                        'Cannot have a bid under the same event/run/parent with the same name'
                    )
                )
            )

        if self.repeat:
            if self.repeat <= Decimal('0.0'):
                errors['repeat'].append(
                    ValidationError(_('Repeat should be a positive value'))
                )
            if not self.istarget:
                errors['repeat'].append(
                    ValidationError(_('Cannot set repeat on non-targets'))
                )
            if self.parent:
                errors['repeat'].append(
                    ValidationError(_('Cannot set repeat on child bids'))
                )
            if self.pk and self.options.exists():
                errors['repeat'].append(
                    ValidationError(_('Cannot set repeat on parent bids'))
                )
            if self.chain:
                errors['repeat'].append(
                    ValidationError(_('Cannot set repeat on chained bids'))
                )
            if self.goal is None:
                errors['repeat'].append(
                    ValidationError(_('Cannot set repeat with no goal'))
                )
            elif self.goal % self.repeat != 0:
                errors['repeat'].append(
                    ValidationError(_('Goal must be a multiple of repeat'))
                )
        else:
            self.repeat = None

        if errors:
            raise ValidationError(errors)

    def save(self, *args, skip_parent=False, **kwargs):
        if self.parent and not skip_parent:
            self.check_parent()
        if self.speedrun:
            self.event = self.speedrun.event
        if self.parent is None and not self.istarget:
            if not self.accepted_number:
                self.accepted_number = 1
        else:
            self.accepted_number = None
        if self.state in ['OPENED', 'CLOSED'] and not self.revealedtime:
            self.revealedtime = util.utcnow()
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
            # TODO: is this correct?
            if not self.speedrun:
                self.speedrun = self.biddependency.speedrun
        if self.chain:
            if self.parent_id is None:
                self.chain_goal = self.goal
            self.chain_remaining = 0
            if self.pk:
                for descendant in self.get_descendants():
                    self.chain_remaining += descendant.goal
        else:
            self.chain_goal = self.chain_remaining = None
        self.update_total()
        if self.state != 'OPENED':
            self.pinned = False
        super(Bid, self).save(*args, **kwargs)
        for option in self.get_children():
            changed = False
            if self.chain:
                old_total = option.total
                option.update_total()
                if old_total != option.total:
                    changed = True
            if option.check_parent() or changed:
                option.save(skip_parent=True)
        if self.parent and not skip_parent:
            self.parent.save()

    def check_parent(self):
        self.parent.refresh_from_db()
        changed = False
        if self.speedrun != self.parent.speedrun:
            self.speedrun = self.parent.speedrun
            changed = True
        # if speedrun is set, event propagates from it
        if not self.speedrun and self.event != self.parent.event:
            self.event = self.parent.event
            changed = True
        if self.state not in ['PENDING', 'DENIED'] and self.state != self.parent.state:
            self.state = self.parent.state
            changed = True
        if self.pinned != self.parent.pinned:
            self.pinned = self.parent.pinned
            changed = True
        if self.chain != self.parent.chain:
            self.chain = self.parent.chain
            changed = True
        if self.chain:
            expected = self.parent.chain_goal + self.goal
            if self.chain_goal != expected:
                self.chain_goal = expected
                changed = True

        return changed

    def update_total(self):
        if not self.pk:
            self.total = 0
            self.count = 0
        elif self.istarget:
            bids = self.bids.completed().aggregate(
                total=Coalesce(Sum('amount'), Decimal(0)), count=Count('amount')
            )
            self.total = bids['total']
            self.count = bids['count']
            # auto close and unpin this if it's a challenge with no children and the goal's been met
            if (
                self.goal
                and self.state == 'OPENED'
                and self.total
                >= (self.chain_goal + self.chain_remaining if self.chain else self.goal)
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
        elif self.chain:
            self.total = max(0, self.parent.total - self.parent.goal)
        else:
            options = self.options.exclude(state__in=('DENIED', 'PENDING')).aggregate(
                total=Coalesce(Sum('total'), Decimal(0)),
                count=Coalesce(Sum('count'), 0),
            )
            self.total = options['total']
            self.count = options['count']

    def full_label(self, addMoney=True):
        result = [self.fullname()]
        if self.speedrun:
            result = [self.speedrun.name_with_category, ' : '] + result
        if addMoney:
            result += [' $', '%0.2f' % self.total]
            if self.goal:
                result += [' / ', '%0.2f' % self.goal]
        return ''.join(result)

    def __str__(self):
        if self.parent:
            return f'{self.parent} (Parent) -- {self.name}'
        elif self.speedrun:
            return f'{self.speedrun.name_with_category} (Run) -- {self.name}'
        else:
            return f'{self.event} (Event) -- {self.name}'

    def fullname(self):
        parent = self.parent.fullname() + ' -- ' if self.parent else ''
        return parent + self.name


class DonationBidQuerySet(models.QuerySet):
    def completed(self):
        return self.filter(donation__transactionstate='COMPLETED')

    def public(self):
        return self.completed().filter(bid__state__in=Bid.PUBLIC_STATES)


class DonationBid(models.Model):
    objects = models.Manager.from_queryset(DonationBidQuerySet)()
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
        if not self.bid_id or not self.donation_id:
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
