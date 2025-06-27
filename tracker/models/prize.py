import datetime
import logging
import operator
from collections import defaultdict
from decimal import Decimal
from functools import reduce

from django.contrib.auth.models import User
from django.core.exceptions import (
    NON_FIELD_ERRORS,
    ImproperlyConfigured,
    ValidationError,
)
from django.db import models
from django.db.models import Case, Count, F, Q, Sum, When
from django.db.models.functions import Coalesce
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.urls import reverse

from tracker import settings, util
from tracker.models import Donation, Event, SpeedRun
from tracker.validators import nonzero, positive

from .util import LatestEvent

__all__ = [
    'Prize',
    'PrizeKey',
    'PrizeClaim',
    'DonorPrizeEntry',
]

logger = logging.getLogger(__name__)

USER_MODEL_NAME = getattr(settings, 'AUTH_USER_MODEL', User)


class PrizeQuerySet(models.QuerySet):
    PUBLIC_FEEDS = ('public', 'current')
    HIDDEN_FEEDS = ('to_draw', 'pending', 'all')
    ALL_FEEDS = PUBLIC_FEEDS + HIDDEN_FEEDS

    def public(self, include_draft=False):
        q = Q(state='ACCEPTED', acceptemailsent=True)
        if not include_draft:
            q &= Q(event__draft=False)
        return self.filter(q)

    def current(self, time=None, *, run=None):
        # current implies 'public', since it should only list prizes that are
        #  available to donate for
        if run is None:
            time = util.parse_time(time)
        else:
            if run.order is None:
                raise ValueError('provided Run is not ordered')
            time = run.starttime
        return self.public().filter(
            Q(startrun__starttime__lte=time, endrun__endtime__gte=time)
            | Q(starttime__lte=time, endtime__gte=time)
            | Q(
                startrun__isnull=True,
                endrun__isnull=True,
                starttime__isnull=True,
                endtime__isnull=True,
            ),
            # accounts for event-wide prizes that have been drawn, though in practice donations
            #  probably should have been turned off, so this may not matter
            claims=None,
            event__allow_donations=True,
        )

    def time_annotation(self):
        return self.annotate(
            draw_time=Coalesce(
                'event__prize_drawing_date',
                'endtime',
                'endrun__endtime',
                output_field=models.DateTimeField(),
            )
        )

    def winner_annotations(self, time=None):
        time = util.parse_time(time)
        return self.annotate(
            accept_count=Coalesce(Sum('claims__acceptcount'), 0),
            pending_count=Coalesce(
                Sum(
                    'claims__pendingcount',
                    filter=~Q(claims__acceptdeadline__lte=time),
                ),
                0,
            ),
            expired_count=Coalesce(
                Sum('claims__pendingcount', filter=Q(claims__acceptdeadline__lte=time)),
                0,
            ),
            decline_count=Coalesce(
                Sum('claims__declinecount'),
                0,
            ),
        )

    def claim_annotations(self, time=None):
        time = util.parse_time(time)
        return self.winner_annotations(time).annotate(
            winner_email_pending=Coalesce(
                Sum(
                    'claims__pendingcount',
                    filter=Q(claims__winneremailsent=False),
                ),
                0,
            ),
            accept_email_sent_count=Coalesce(Sum('claims__acceptemailsentcount'), 0),
            accept_email_pending=Case(
                When(accept_email_sent_count__lt=F('accept_count'), then=True),
                default=False,
                output_field=models.BooleanField(),
            ),
            needs_shipping=Count(
                'claims',
                filter=Q(
                    claims__acceptcount=F('claims__acceptemailsentcount'),
                    claims__acceptcount__gt=0,
                    claims__shippingstate='PENDING',
                ),
            ),
            shipped_email_pending=Count(
                'claims',
                filter=Q(
                    claims__shippingstate__in=('SHIPPED', 'AWARDED'),
                    claims__shippingemailsent=False,
                ),
            ),
        )

    def to_draw(self, time=None):
        time = util.parse_time(time)
        return (
            self.public()
            .time_annotation()
            .filter(
                # TODO: figure out how to use the winner_annotations for this
                (
                    Q(claims=None)
                    | (
                        Q(claims__pendingcount__gt=0)
                        & Q(claims__acceptdeadline__lt=time)
                    )
                )
                & (Q(draw_time=None) | Q(draw_time__lte=time)),
                state='ACCEPTED',
            )
        )

    def pending(self):
        return self.filter(state='PENDING')

    def contributor_email_pending(self):
        return self.filter(
            state__in=('ACCEPTED', 'DENIED'),
            acceptemailsent=False,
            claims=None,
        )

    def lifecycle(self, states=None, /, time=None):
        if states is None:
            return self
        lookups = PrizeManager.lifecycle_lookups()
        if isinstance(states, str):
            states = [states]
        states = [s.lower().strip() for s in states if s]
        parts = []
        annotated = self.claim_annotations()
        if states == ['archived']:
            return annotated.filter(
                event__archived=True,
                state='ACCEPTED',
                acceptemailsent=True,
            ).filter(
                Q(
                    maxwinners__gt=F('accept_count')
                )  # unclaimed copies (either undrawn or unclaimed by winners)
                | Q(
                    accept_email_sent_count__lt=F('accept_count')
                )  # handler never notified
                | Q(
                    needs_shipping__gt=0,
                )  # prize never shipped
                | Q(
                    shipped_email_pending__gt=0,
                )  # shipping/key info never provided)
            )
        for state in states:
            if state not in (lu[0] for lu in lookups):
                raise ValueError(
                    f'Invalid parameter, got `{state}`, expected one of {", ".join(f"`{lu[0]}`" for lu in lookups)}'
                )
            if state == 'archived':
                raise ValueError('Can only search for `archived` lifecycle on its own')
            elif state == 'pending':
                parts.append(self.pending())
            elif state == 'notify_contributor':
                parts.append(self.contributor_email_pending())
            elif state == 'denied':
                parts.append(self.filter(state='DENIED', acceptemailsent=True))
            elif state == 'accepted':
                parts.append(
                    self.filter(
                        state='ACCEPTED', acceptemailsent=True, claims=None
                    ).exclude(id__in=self.to_draw(time))
                )
            elif state == 'ready':
                parts.append(self.to_draw(time))
            else:
                if state == 'drawn':
                    parts.append(annotated.filter(winner_email_pending__gt=0))
                elif state == 'winner_notified':
                    parts.append(
                        annotated.filter(winner_email_pending=0, pending_count__gt=0)
                    )
                elif state == 'claimed':
                    parts.append(annotated.filter(accept_email_pending=True))
                elif state == 'needs_shipping':
                    parts.append(annotated.filter(needs_shipping__gt=0))
                elif state == 'shipped':
                    parts.append(annotated.filter(shipped_email_pending__gt=0))
                elif state == 'completed':
                    parts.append(
                        annotated.filter(
                            winner_email_pending=0,
                            maxwinners=F('accept_count'),
                            accept_email_pending=False,
                            needs_shipping=0,
                            shipped_email_pending=0,
                        )
                    )
        if parts:
            return reduce(operator.or_, parts)
        else:
            return self


class PrizeManager(models.Manager):
    @staticmethod
    def lifecycle_lookups():
        return (
            ('pending', 'Pending Acceptance/Denial'),
            ('notify_contributor', 'Needs Contributor Email'),
            ('denied', 'Denied'),
            (
                'accepted',
                'Accepted',
            ),  # accepted, but waiting for the event draw date to pass
            ('ready', 'Ready to Draw'),
            ('drawn', 'Drawn, Needs Winner Email'),
            ('winner_notified', 'Pending Winner Action'),
            ('claimed', 'Claimed, Needs Handler Email'),
            ('needs_shipping', 'Needs Shipping Info'),
            ('shipped', 'Needs Shipped/Awarded Email'),
            ('completed', 'Complete'),
            ('archived', 'Incomplete and Archived'),
        )

    def get_by_natural_key(self, name, event):
        return self.get(name=name, event=Event.objects.get_by_natural_key(*event))


def prize_path_id(i, f):
    return f'prizes/{i.id}/{f}'


def prefer_prize_storage():
    from django.core.files.storage import InvalidStorageError, default_storage, storages

    try:
        return storages['prizes']
    except InvalidStorageError:
        logger.info('no prizes storage, falling back to default')
        return default_storage


class Prize(models.Model):
    PUBLIC_FEEDS = PrizeQuerySet.PUBLIC_FEEDS
    HIDDEN_FEEDS = PrizeQuerySet.HIDDEN_FEEDS
    ALL_FEEDS = PrizeQuerySet.ALL_FEEDS
    PUBLIC_STATES = ('ACCEPTED',)
    HIDDEN_STATES = ('DENIED', 'PENDING', 'FLAGGED')
    ALL_STATES = PUBLIC_STATES + HIDDEN_STATES

    objects = PrizeManager.from_queryset(PrizeQuerySet)()
    name = models.CharField(max_length=64)
    category = models.ForeignKey(
        'PrizeCategory', on_delete=models.PROTECT, null=True, blank=True
    )
    tags = models.ManyToManyField('tracker.Tag', blank=True, related_name='prizes')
    image = models.URLField(max_length=1024, blank=True)
    altimage = models.URLField(
        max_length=1024,
        blank=True,
        verbose_name='Alternate Image',
        help_text='A second image to display in situations where the default image is not appropriate (tight spaces, stream, etc...)',
    )
    imagefile = models.FileField(
        upload_to=prize_path_id, storage=prefer_prize_storage, null=True, blank=True
    )
    description = models.TextField(max_length=1024, blank=True)
    shortdescription = models.TextField(
        max_length=256,
        blank=True,
        verbose_name='Short Description',
        help_text='Alternative description text to display in tight spaces',
    )
    extrainfo = models.TextField(max_length=1024, blank=True)
    estimatedvalue = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        null=True,
        blank=True,
        verbose_name='Estimated Value',
        validators=[positive, nonzero],
    )
    minimumbid = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        default=Decimal('5.00'),
        verbose_name='Minimum Bid',
        validators=[positive, nonzero],
    )
    maximumbid = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        null=True,
        blank=True,
        editable=False,
        default=None,
        verbose_name='DEPRECATED - do not use',
        validators=[positive, nonzero],
    )
    sumdonations = models.BooleanField(default=False, verbose_name='Sum Donations')
    randomdraw = models.BooleanField(default=True, verbose_name='Random Draw')
    event = models.ForeignKey('Event', on_delete=models.PROTECT, default=LatestEvent)
    startrun = models.ForeignKey(
        'SpeedRun',
        on_delete=models.PROTECT,
        related_name='prize_start',
        null=True,
        blank=True,
        verbose_name='Start Run',
    )
    prev_run = models.ForeignKey(
        'SpeedRun',
        on_delete=models.SET_NULL,
        related_name='+',
        null=True,
        blank=True,
        serialize=False,
        editable=False,
    )
    endrun = models.ForeignKey(
        'SpeedRun',
        on_delete=models.PROTECT,
        related_name='prize_end',
        null=True,
        blank=True,
        verbose_name='End Run',
    )
    next_run = models.ForeignKey(
        'SpeedRun',
        on_delete=models.SET_NULL,
        related_name='+',
        null=True,
        blank=True,
        serialize=False,
        editable=False,
    )
    starttime = models.DateTimeField(null=True, blank=True, verbose_name='Start Time')
    endtime = models.DateTimeField(null=True, blank=True, verbose_name='End Time')
    maxwinners = models.IntegerField(
        default=1,
        verbose_name='Max Winners',
        validators=[positive, nonzero],
        blank=False,
        null=False,
    )
    maxmultiwin = models.IntegerField(
        default=1,
        verbose_name='Max Wins per Donor',
        validators=[positive, nonzero],
        blank=False,
        null=False,
        editable=False,
    )
    provider = models.CharField(
        max_length=64,
        blank=True,
        help_text='Name of the person who provided the prize to the event',
    )
    handler = models.ForeignKey(
        USER_MODEL_NAME,
        null=True,
        help_text='User account responsible for prize shipping',
        on_delete=models.PROTECT,
    )
    acceptemailsent = models.BooleanField(
        default=False, verbose_name='Accept/Deny Email Sent'
    )
    creator = models.CharField(
        max_length=64, blank=True, null=True, verbose_name='Creator'
    )
    creatoremail = models.EmailField(
        max_length=128, blank=True, null=True, verbose_name='Creator Email'
    )
    creatorwebsite = models.CharField(
        max_length=128, blank=True, null=True, verbose_name='Creator Website'
    )
    state = models.CharField(
        max_length=32,
        choices=(
            ('PENDING', 'Pending'),
            ('ACCEPTED', 'Accepted'),
            ('DENIED', 'Denied'),
            ('FLAGGED', 'Flagged'),
        ),
        default='PENDING',
    )
    requiresshipping = models.BooleanField(
        default=True, verbose_name='Requires Postal Shipping'
    )
    reviewnotes = models.TextField(
        max_length=1024,
        null=False,
        blank=True,
        verbose_name='Review Notes',
        help_text='Notes for the contributor (for example, why a particular prize was denied)',
    )
    custom_country_filter = models.BooleanField(
        default=False,
        verbose_name='Use Custom Country Filter',
        help_text='If checked, use a different country filter than that of the event.',
    )
    allowed_prize_countries = models.ManyToManyField(
        'Country',
        blank=True,
        verbose_name='Prize Countries',
        help_text='List of countries whose residents are allowed to receive prizes (leave blank to allow all countries)',
    )
    disallowed_prize_regions = models.ManyToManyField(
        'CountryRegion',
        blank=True,
        verbose_name='Disallowed Regions',
        help_text='A blacklist of regions within allowed countries that are not allowed for drawings (e.g. Quebec in Canada)',
    )
    key_code = models.BooleanField(
        default=False,
        help_text='If true, this prize is a key code of some kind rather '
        'than a physical prize. Disables multiwin and locks max '
        'winners to the number of keys available.',
    )

    class Meta:
        app_label = 'tracker'
        ordering = ['event__datetime', 'startrun__starttime', 'starttime', 'name']
        unique_together = ('name', 'event')

    @property
    def lifecycle(self):
        if not hasattr(self, 'accept_count') or not hasattr(self, 'draw_time'):
            raise AttributeError(
                'fetch the queryset with `claim_annotations` and `time_annotation` before using this property'
            )
        if self.state in ['PENDING', 'FLAGGED']:
            return 'pending'
        else:
            now = util.utcnow()
            if not self.acceptemailsent:
                return 'notify_contributor'
            elif self.state == 'DENIED':
                return 'denied'
            elif self.draw_time is not None and self.draw_time > now:
                return 'accepted'
            elif self.maxwinners > self.accept_count + self.pending_count:
                return 'ready'
            elif self.winner_email_pending > 0:
                return 'drawn'
            elif self.pending_count > 0:
                return 'winner_notified'
            elif self.accept_email_pending > 0:
                return 'claimed'
            elif self.needs_shipping > 0:
                return 'needs_shipping'
            elif self.shipped_email_pending > 0:
                return 'shipped'
            else:
                return 'completed'

    @property
    def public(self):
        return self.state == 'ACCEPTED'

    def natural_key(self):
        return self.name, self.event.natural_key()

    def get_absolute_url(self):
        return util.build_public_url(reverse('tracker:prize', args=(self.id,)))

    def __str__(self):
        return str(self.name)

    @property
    def start_time_utc(self):
        return self.starttime.astimezone(datetime.timezone.utc)

    @property
    def end_time_utc(self):
        return self.endtime.astimezone(datetime.timezone.utc)

    def clean(self, winner=None):
        if not settings.TRACKER_SWEEPSTAKES_URL:
            raise ValidationError(
                'Cannot create prizes without a TRACKER_SWEEPSTAKES_URL in settings.'
            )
        errors = defaultdict(list)

        if self.maximumbid is not None and self.maximumbid != self.minimumbid:
            errors['maximumbid'].append('Do not use this field.')
        if self.handler_id and not self.handler.is_active:
            errors['handler'].append('Handler accounts need to be active.')
        if (self.startrun_id is None) != (self.endrun_id is None):
            errors['startrun'].append(
                'Must have both Start Run and End Run set, or neither.'
            )
        if (
            self.startrun_id
            and self.startrun.order
            and self.endrun_id
            and self.endrun.order
            and self.startrun.order > self.endrun.order
        ):
            errors['startrun'].append('Start Run must begin sooner than End Run')
        if self.startrun_id and self.event_id != self.startrun.event_id:
            errors['startrun'].append('Prize Event must be the same as Start Run Event')
        if self.endrun_id and self.event_id != self.endrun.event_id:
            errors['endrun'].append('Prize Event must be the same as End Run Event')
        if self.startrun_id and self.startrun.order is None:
            errors['startrun'].append('Start Run must be ordered')
        if self.endrun_id and self.endrun.order is None:
            errors['endrun'].append('End Run must be ordered')
        if (self.starttime is None) != (self.endtime is None):
            errors['starttime'].append(
                'Must have both Start Time and End Time set, or neither'
            )
        if self.starttime and self.starttime > self.endtime:
            errors['starttime'].append('Prize Start Time must be later than End Time')
        if self.startrun_id and self.starttime:
            errors['starttime'].append(
                'Cannot have both Start/End Run and Start/End Time set'
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not settings.TRACKER_SWEEPSTAKES_URL:
            raise ImproperlyConfigured(
                'Cannot create prizes without a TRACKER_SWEEPSTAKES_URL in settings'
            )

        using = kwargs.get('using', None)
        if self.startrun and self.startrun.order and self.endrun and self.endrun.order:
            self.prev_run = (
                SpeedRun.objects.using(using)
                .filter(event=self.startrun.event_id, order__lt=self.startrun.order)
                .order_by('order')
                .last()
            )
            self.next_run = (
                SpeedRun.objects.using(using)
                .filter(event=self.endrun.event_id, order__gt=self.endrun.order)
                .order_by('order')
                .first()
            )
        else:
            self.prev_run = self.next_run = None
        if self.key_code:
            self.requiresshipping = False
        if self.pk and self.handler_id == self.event.prizecoordinator_id:
            # don't need to notify handler if it's the prize coordinator
            self.claims.update(acceptemailsentcount=F('acceptcount'))
        super(Prize, self).save(*args, **kwargs)

    def eligible_donors(self) -> dict[models.Model, Decimal]:
        donations = Donation.objects.filter(
            event=self.event, transactionstate='COMPLETED'
        ).select_related('donor')

        # Apply the country/region filter to the drawing
        if self.custom_country_filter:
            country_filter = self.allowed_prize_countries.all()
            region_filter = self.disallowed_prize_regions.all()
        else:
            country_filter = self.event.allowed_prize_countries.all()
            region_filter = self.event.disallowed_prize_regions.all()

        if country_filter.exists():
            donations = donations.filter(donor__addresscountry__in=country_filter)
        if region_filter.exists():
            donations = donations.filter(
                *(
                    ~Q(
                        donor__addresscountry=region.country,
                        donor__addressstate__iexact=region.name,
                    )
                    for region in region_filter
                )
            )

        donations = donations.exclude(donor__in=[w.winner for w in self.claims.all()])
        if self.has_draw_time():
            donations = donations.filter(
                timereceived__gte=self.start_draw_time(),
                timereceived__lte=self.end_draw_time(),
            )
        donors = defaultdict(lambda: Decimal('0.0'))
        for donation in donations:
            if self.sumdonations:
                donors[donation.donor] += donation.amount
            else:
                donors[donation.donor] = max(donation.amount, donors[donation.donor])
        direct_entries = DonorPrizeEntry.objects.filter(prize=self).exclude(
            donor__in=[w.winner for w in self.claims.all()]
        )
        for entry in direct_entries:
            donors[entry.donor] = max(self.minimumbid, donors[entry.donor])
        if not donors:
            return {}
        elif self.randomdraw:

            return {
                donor: amount
                for donor, amount in donors.items()
                if self.minimumbid <= amount
            }
        else:

            donor, amount = max(donors.items(), key=lambda i: i[1])
            return {donor: amount}

    def is_donor_allowed_to_receive(self, donor):
        return self.is_country_region_allowed(donor.addresscountry, donor.addressstate)

    def is_country_region_allowed(self, country, region):
        return self.is_country_allowed(
            country
        ) and not self.is_country_region_disallowed(country, region)

    def is_country_allowed(self, country):
        if self.requiresshipping:
            if self.custom_country_filter:
                allowedCountries = self.allowed_prize_countries.all()
            else:
                allowedCountries = self.event.allowed_prize_countries.all()
            if allowedCountries.exists() and country not in allowedCountries:
                return False
        return True

    def is_country_region_disallowed(self, country, region):
        if self.requiresshipping:
            if self.custom_country_filter:
                disallowedRegions = self.disallowed_prize_regions.all()
            else:
                disallowedRegions = self.event.disallowed_prize_regions.all()
            for badRegion in disallowedRegions:
                if (
                    country == badRegion.country
                    and region.lower() == badRegion.name.lower()
                ):
                    return True
        return False

    def has_draw_time(self):
        return self.start_draw_time() and self.end_draw_time()

    def start_draw_time(self):
        if self.startrun_id:
            if self.prev_run:
                # allow some slop into the previous run's setup time in case the run starts 'late'
                return self.prev_run.endtime - datetime.timedelta(
                    milliseconds=self.prev_run.setup_time_ms
                )
            return self.startrun.start_time_utc
        elif self.starttime:
            return self.start_time_utc
        else:
            return None

    def end_draw_time(self):
        if self.endrun_id:
            if not self.next_run:
                # covers finale speeches
                return self.endrun.end_time_utc + datetime.timedelta(hours=1)
            return self.endrun.end_time_utc
        elif self.endtime:
            return self.end_time_utc
        else:
            return None

    def contains_draw_time(self, time):
        return not self.has_draw_time() or (
            self.start_draw_time() <= time <= self.end_draw_time()
        )

    def current_win_count(self):
        return sum(
            x.pendingcount + x.acceptcount
            for x in self.get_prize_claims()
            if x is not None
        )

    def maxed_winners(self):
        return self.current_win_count() == self.maxwinners

    def get_prize_claims(self, time=None):
        """returns accepted, or pending-and-not-expired claims"""
        return [c for c in self.claims.all() if c.accepted or c.pending(time)]

    def get_pending_claims(self, time=None):
        return [c for c in self.claims.all() if c.pending(time)]

    def get_expired_claims(self, time=None):
        return [c for c in self.claims.all() if c.expired(time)]

    def get_accepted_claims(self):
        return [c for c in self.claims.all() if c.accepted]

    def is_pending_shipping(self):
        return any(
            c for c in self.get_accepted_claims() if c.shippingstate == 'PENDING'
        )

    def is_fully_shipped(self):
        return (
            self.requiresshipping
            and self.maxed_winners()
            and not self.is_pending_shipping()
        )

    def get_winners(self):
        """accepted, or pending-but-not-expired winners"""
        return [w.winner for w in self.get_prize_claims()]


@receiver(post_save, sender=SpeedRun)
def fix_prev_and_next_run_save(sender, instance, created, raw, using, **kwargs):
    if raw:
        return
    fix_prev_and_next_run(instance, using)


@receiver(post_delete, sender=SpeedRun)
def fix_prev_and_next_run_delete(sender, instance, using, **kwargs):
    fix_prev_and_next_run(instance, using)


def fix_prev_and_next_run(instance, using):
    prev_run = instance.order and (
        SpeedRun.objects.filter(event=instance.event_id, order__lt=instance.order)
        .using(using)
        .order_by('order')
        .last()
    )
    next_run = instance.order and (
        SpeedRun.objects.filter(event=instance.event_id, order__gt=instance.order)
        .using(using)
        .order_by('order')
        .first()
    )
    prizes = Prize.objects.using(using).filter(
        Q(prev_run=instance)
        | Q(next_run=instance)
        | Q(startrun=instance)
        | Q(endrun=instance)
    )
    if prev_run:
        prizes = prizes | Prize.objects.using(using).filter(
            Q(startrun=next_run) | Q(endrun=prev_run)
        )
    for prize in prizes:
        prize.save(using=using)


class PrizeKey(models.Model):
    prize = models.ForeignKey(
        'Prize', on_delete=models.PROTECT, related_name='prize_keys'
    )
    prize_claim = models.OneToOneField(
        'tracker.PrizeClaim',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='prize_key',
    )
    key = models.CharField(max_length=64, unique=True)

    class Meta:
        app_label = 'tracker'
        verbose_name = 'Prize Key'
        ordering = ['prize']
        # TODO: permissions are currently useless, consider removing
        permissions = (
            ('edit_prize_key_keys', 'Can edit existing prize keys'),
            ('remove_prize_key_winners', 'Can remove winners from prize keys'),
        )

    def create_winner(self, winner) -> 'PrizeClaim':
        """creates a PrizeClaim with all the fields set"""
        assert self.prize_claim_id is None, 'key already has a claim'
        # keys cannot be declined and don't need to be shipped, so they skip half of the prize lifecycle
        self.prize_claim = PrizeClaim.objects.create(
            prize=self.prize,
            winner=winner,
        )
        self.save()
        return self.prize_claim

    @property
    def winner(self):
        return self.prize_claim_id and self.prize_claim.winner

    def __str__(self):
        return f'{self.prize}: ****{self.key[-4:]}'


@receiver(post_save, sender=Prize)
@receiver(post_save, sender=PrizeKey)
def set_max_winners(sender, instance, created, raw, **kwargs):
    if raw:
        return
    if sender == Prize:
        if not instance.key_code:
            return
        prize = instance
    elif sender == PrizeKey:
        if not created:
            return
        prize = instance.prize
    else:
        assert False, 'sender was neither Prize nor PrizeKey'
    count = prize.prize_keys.count()
    changed = False
    if prize.maxwinners != count:
        prize.maxwinners = count
        changed = True
    if changed:
        prize.save()


class PrizeClaimQuerySet(models.QuerySet):
    def claimed(self):
        return self.filter(acceptcount__gt=0)

    def pending(self, time=None):
        time = util.parse_time(time)
        return self.filter(
            Q(pendingcount__gt=0)
            & (Q(acceptdeadline=None) | Q(acceptdeadline__gt=time))
        )

    def expired(self, time=None):
        time = util.parse_time(time)
        return self.filter(pendingcount__gt=0, acceptdeadline__lt=time)

    def decline_expired(self, time=None):
        return self.expired(time).update(declinecount=F('pendingcount'), pendingcount=0)

    def claimed_or_pending(self):
        return self.claimed() | self.pending()

    def winner_email_pending(self):
        return self.pending().filter(winneremailsent=False)

    def accept_email_pending(self):
        return self.filter(
            acceptcount__gt=F('acceptemailsentcount'),
        )

    def needs_shipping(self):
        return self.filter(
            acceptemailsentcount__gt=0,
            acceptcount__gt=0,
            shippingstate='PENDING',
        )

    def shipped_email_pending(self):
        return self.filter(
            shippingstate__in=('SHIPPED', 'AWARDED'),
            shippingemailsent=False,
        )

    def completed(self):
        return self.filter(
            shippingstate__in=('SHIPPED', 'AWARDED', 'N/A'),
            shippingemailsent=True,
        )

    def archived(self):
        # skip pending/denied prizes
        # skip prizes that are fully shipped/awarded
        # skip prizes that don't need shipping where the handler has been notified
        # skip prizes that have no active claims
        return (
            self.exclude(prize__state__in=('PENDING', 'DENIED'))
            .exclude(shippingstate__in=('SHIPPED', 'AWARDED'), shippingemailsent=True)
            .exclude(shippingstate='N/A', acceptemailsentcount=F('acceptcount'))
            .filter(acceptcount__gt=0, event__archived=True)
        )


class PrizeClaim(models.Model):
    objects = models.Manager.from_queryset(PrizeClaimQuerySet)()
    winner = models.ForeignKey(
        'Donor',
        null=False,
        blank=False,
        on_delete=models.PROTECT,
        related_name='prizeclaims',
    )
    pendingcount = models.IntegerField(
        default=1,
        null=False,
        blank=False,
        validators=[positive],
        verbose_name='Pending Count',
        help_text='The number of pending wins this donor has on this prize.',
    )
    acceptcount = models.IntegerField(
        default=0,
        null=False,
        blank=False,
        validators=[positive],
        verbose_name='Accept Count',
        help_text='The number of copies this winner has won and accepted.',
    )
    declinecount = models.IntegerField(
        default=0,
        null=False,
        blank=False,
        validators=[positive],
        verbose_name='Decline Count',
        help_text='The number of declines this donor has put towards this prize. '
        'Set it to the max prize multi win amount to prevent this donor '
        'from being entered from future drawings.',
    )
    prize = models.ForeignKey(
        'Prize',
        null=False,
        blank=False,
        on_delete=models.PROTECT,
        related_name='claims',
    )
    winneremailsent = models.BooleanField(
        default=False, verbose_name='Winner Notification Email Sent'
    )
    # this is an integer because we want to re-send on each different number of accepts
    acceptemailsentcount = models.IntegerField(
        default=0,
        null=False,
        blank=False,
        validators=[positive],
        verbose_name='Accept Count Sent For',
        help_text='The number of accepts that the previous e-mail was sent '
        'for (or 0 if none were sent yet).',
    )
    # also used for awarding digital keys
    shippingemailsent = models.BooleanField(
        default=False, verbose_name='Shipping Email Sent'
    )
    couriername = models.CharField(
        max_length=64,
        verbose_name='Courier Service Name',
        help_text='e.g. FedEx, DHL, ...',
        blank=True,
        null=False,
    )
    trackingnumber = models.CharField(
        max_length=64, verbose_name='Tracking Number', blank=True, null=False
    )
    shippingstate = models.CharField(
        max_length=64,
        verbose_name='Shipping State',
        choices=(
            ('PENDING', 'Pending'),
            ('SHIPPED', 'Shipped'),
            ('AWARDED', 'Awarded'),
            ('N/A', 'N/A'),
        ),
        default='PENDING',
    )
    shippingcost = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        null=True,
        blank=True,
        verbose_name='Shipping Cost',
        validators=[positive, nonzero],
    )
    winnernotes = models.TextField(
        max_length=1024, verbose_name='Winner Notes', null=False, blank=True
    )
    shippingnotes = models.TextField(
        max_length=2048, verbose_name='Shipping Notes', null=False, blank=True
    )
    acceptdeadline = models.DateTimeField(
        verbose_name='Winner Accept Deadline',
        default=None,
        null=True,
        blank=True,
        help_text='The deadline for this winner to accept their prize '
        '(leave blank for no deadline)',
    )
    auth_code = models.CharField(
        max_length=64,
        blank=False,
        null=False,
        editable=False,
        default=util.make_auth_code,
        help_text='Used instead of a login for winners to manage prizes.',
    )
    shipping_receipt_url = models.URLField(
        max_length=1024,
        blank=True,
        null=False,
        verbose_name='Shipping Receipt Image URL',
        help_text='The URL of an image of the shipping receipt',
    )

    class Meta:
        app_label = 'tracker'
        verbose_name = 'Prize Claim'
        unique_together = (
            'prize',
            'winner',
        )

    def __init__(self, *args, **kwargs):
        if kwargs.get('acceptcount', 0) or kwargs.get('declinecount', 0):
            kwargs.setdefault('pendingcount', 0)
        super().__init__(*args, **kwargs)

    @property
    def state(self):
        if self.acceptcount:
            return 'ACCEPTED'
        elif self.declinecount:
            return 'DECLINED'
        else:
            return 'PENDING'

    @property
    def event(self):
        return self.prize.event

    @property
    def requiresshipping(self):
        return self.prize.requiresshipping

    @property
    def winner_email_pending(self):
        # TODO: check for expired claims?
        return self.pendingcount > 0 and not self.winneremailsent

    @property
    def accept_email_pending(self):
        return self.acceptcount > self.acceptemailsentcount

    @property
    def shipped_email_pending(self):
        return (
            self.shippingstate in ('SHIPPED', 'AWARDED') and not self.shippingemailsent
        )

    @property
    def accepted(self):
        return self.acceptcount > 0

    @property
    def declined(self):
        return self.declinecount > 0

    def pending(self, time=None):
        time = util.parse_time(time)
        return self.pendingcount > 0 and (
            self.acceptdeadline is None or self.acceptdeadline > time
        )

    def expired(self, time=None):
        time = util.parse_time(time)
        return (
            self.pendingcount > 0
            and self.acceptdeadline is not None
            and self.acceptdeadline < time
        )

    def create_claim_url(self, request):
        self._claim_url = util.build_public_url(
            reverse('tracker:prize_winner', args=(self.pk,))
            + f'?auth_code={self.auth_code}',
            request,
        )

    @property
    def claim_url(self):
        if not hasattr(self, '_claim_url'):
            raise AttributeError(
                'you must call `create_claim_url` with the proper request before retrieving this property'
            )
        return self._claim_url

    def accept_deadline_date(self):
        """Return the actual calendar date associated with the accept deadline"""
        if self.acceptdeadline:
            return self.acceptdeadline.astimezone(util.anywhere_on_earth_tz()).date()
        else:
            return None

    def clean(self):
        errors = defaultdict(list)
        agg = self.prize.claims.exclude(pk=self.pk).aggregate(
            accept=Coalesce(Sum('acceptcount'), 0),
            pending=Coalesce(Sum('pendingcount'), 0),
        )
        if self.acceptcount + self.pendingcount + self.declinecount != 1:
            errors[NON_FIELD_ERRORS].append('State counts should add up to 1')
        if (
            self.acceptcount + self.pendingcount + agg['accept'] + agg['pending']
            > self.prize.maxwinners
        ):
            errors[NON_FIELD_ERRORS].append(
                'Number of prize winners is greater than the maximum for this prize.'
            )
        if self.trackingnumber and not self.couriername:
            errors['trackingnumber'].append(
                'A tracking number is only useful with a courier name as well!'
            )
        if self.requiresshipping and self.shippingstate not in ('SHIPPED', 'PENDING'):
            errors['shippingstate'].append('Invalid shipping state for physical prize')
        if (
            self.winner
            and self.acceptcount > 0
            and self.prize.requiresshipping
            and not self.prize.is_country_region_allowed(
                self.winner.addresscountry, self.winner.addressstate
            )
        ):
            message = 'Unfortunately, for legal or logistical reasons, we cannot ship this prize to that region. Please accept our deepest apologies.'
            coordinator = self.prize.event.prizecoordinator
            if coordinator:
                message += ' If you have any questions, please contact our prize coordinator at {0}'.format(
                    coordinator.email
                )
            errors[NON_FIELD_ERRORS].append(message)
        if self.prize.key_code and not hasattr(self, 'prize_key'):
            errors[NON_FIELD_ERRORS].append(
                'Prize claims attached to key code prizes need a prize key attached as well.'
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.prize.key_code:
            # skip a bunch of stuff that's not relevant for key codes
            self.acceptcount = 1
            self.pendingcount = 0
            self.declinecount = 0
            self.winneremailsent = True
            self.acceptemailsentcount = 1
            self.shippingstate = 'AWARDED'
        elif not self.requiresshipping:
            # digital prizes can skip the shipping step entirely
            self.shippingstate = 'N/A'
            self.shippingemailsent = True
        if self.prize.handler == self.prize.event.prizecoordinator:
            # don't need to notify the coordinator if they're the same as the handler
            self.acceptemailsentcount = self.acceptcount
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.prize} -- {self.winner}'


class PrizeCategoryManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)

    def get_or_create_by_natural_key(self, name):
        return self.get_or_create(name=name)


class PrizeCategory(models.Model):
    objects = PrizeCategoryManager()
    name = models.CharField(max_length=64, unique=True)

    class Meta:
        app_label = 'tracker'
        verbose_name = 'Prize Category'
        verbose_name_plural = 'Prize Categories'

    def natural_key(self):
        return (self.name,)

    def __str__(self):
        return self.name


class DonorPrizeEntry(models.Model):
    donor = models.ForeignKey('Donor', on_delete=models.PROTECT)
    prize = models.ForeignKey('Prize', on_delete=models.PROTECT)
    weight = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        null=True,
        default=None,
        verbose_name='Entry Weight',
        validators=[positive, nonzero],
        help_text='DEPRECATED - do not use',
        editable=False,
    )

    class Meta:
        app_label = 'tracker'
        verbose_name = 'Donor Prize Entry'
        verbose_name_plural = 'Donor Prize Entries'
        unique_together = (
            'prize',
            'donor',
        )

    @property
    def event(self):
        return self.prize.event

    def __str__(self):
        return f'{self.donor} entered to win {self.prize}'
