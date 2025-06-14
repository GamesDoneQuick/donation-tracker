import datetime
from collections import defaultdict
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import (
    NON_FIELD_ERRORS,
    ImproperlyConfigured,
    ValidationError,
)
from django.db import models
from django.db.models import F, Q, Sum
from django.db.models.functions import Coalesce
from django.db.models.lookups import Exact
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
    'PrizeCategory',
    'DonorPrizeEntry',
]

USER_MODEL_NAME = getattr(settings, 'AUTH_USER_MODEL', User)


class PrizeQuerySet(models.QuerySet):
    PUBLIC_FEEDS = ('public', 'current')
    HIDDEN_FEEDS = ('to_draw', 'pending', 'all')
    ALL_FEEDS = PUBLIC_FEEDS + HIDDEN_FEEDS

    def public(self, include_draft=False):
        qs = self
        if not include_draft:
            qs = self.filter(event__draft=False)
        return qs.filter(state='ACCEPTED')

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
            Q(claims=None)
            & (
                Q(startrun__starttime__lte=time, endrun__endtime__gte=time)
                | Q(starttime__lte=time, endtime__gte=time)
                | Q(
                    startrun__isnull=True,
                    endrun__isnull=True,
                    starttime__isnull=True,
                    endtime__isnull=True,
                )
            )
        )

    def to_draw(self, time=None):
        time = util.parse_time(time)
        return self.filter(
            (
                Q(claims=None)
                | (Q(claims__pendingcount__gt=0) & Q(claims__acceptdeadline__lt=time))
            )
            & (
                Q(endrun__endtime__lte=time)
                | Q(endtime__lte=time)
                | (Q(endtime=None) & Q(endrun=None))
            )
            & (
                Q(event__prize_drawing_date=None)
                | Q(event__prize_drawing_date__lte=time)
            ),
            state='ACCEPTED',
        )

    def pending(self):
        return self.filter(state='PENDING')

    def contributor_email_pending(self):
        return self.filter(
            state__in=('ACCEPTED', 'DENIED'),
            acceptemailsent=False,
            claims=None,
            event__archived=False,
        )

    def email_state(self, state):
        if state is None:
            return self
        lookups = PrizeManager.email_state_lookups()
        if state not in (lu[0] for lu in lookups):
            raise ValueError(
                f'Invalid parameter, got `{state}`, expected one of {", ".join(f"`{lu[0]}`" for lu in lookups)}'
            )
        if state == 'contributor':
            return self.contributor_email_pending()
        else:
            claims = PrizeClaim.objects.filter(prize__in=self)
            if state == 'winner':
                claims = claims.winner_email_pending()
            elif state == 'accepted':
                claims = claims.accept_email_pending()
            elif state == 'shipped':
                claims = claims.shipped_email_pending()
            return self.filter(id__in=(c.prize_id for c in claims))


class PrizeManager(models.Manager):
    @staticmethod
    def email_state_lookups():
        return (
            ('contributor', 'Needs Contributor Email'),
            ('winner', 'Needs Winner Email'),
            ('accepted', 'Needs Handler Email'),
            ('shipped', 'Needs Shipped/Awarded Email'),
        )

    def get_by_natural_key(self, name, event):
        return self.get(name=name, event=Event.objects.get_by_natural_key(*event))


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
    imagefile = models.FileField(upload_to='prizes', null=True, blank=True)
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
        if self.maxmultiwin > 1 and self.category_id is not None:
            errors['maxmultiwin'].append(
                'A donor may not win more than one prize of any category, so setting a prize '
                'to have multiple wins per single donor with a non-null category is incompatible.'
            )
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
        super(Prize, self).save(*args, **kwargs)

    def eligible_donors(self) -> dict[models.Model, Decimal]:
        donations = Donation.objects.filter(
            event=self.event, transactionstate='COMPLETED'
        ).select_related('donor')
        # remove all donations from donors who have won a prize under the same category for this event
        if self.category is not None:
            donations = donations.exclude(
                donor__claims__prize__category=self.category,
                donor__claims__prize__event=self.event,
            )

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

        full_claims = [c for c in self.claims.all() if c.full]
        donations = donations.exclude(donor__in=[w.winner for w in full_claims])
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
            donor__in=[w.winner for w in full_claims]
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

    def create_winner(self, winner):
        """creates a PrizeClaim with all the fields set"""
        # TODO?: bulk_create? It's not like this is something that gets called a lot
        assert self.prize_claim_id is None, 'key already has a claim'
        self.prize_claim = PrizeClaim.objects.create(
            prize=self.prize,
            winner=winner,
            pendingcount=0,
            acceptcount=1,
            winneremailsent=True,
            acceptemailsentcount=1,
            shippingstate='SHIPPED',
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
    if prize.maxmultiwin != 1:
        prize.maxmultiwin = 1
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
        # key codes cannot be declined
        return self.pending().filter(
            prize__event__archived=False, prize__key_code=False, winneremailsent=False
        )

    def accept_email_pending(self):
        # key codes cannot be declined
        return self.annotate(
            handler_is_coordinator=Exact(
                F('prize__handler_id'),
                Coalesce(F('prize__event__prizecoordinator_id'), 0),
            )
        ).filter(
            handler_is_coordinator=False,
            prize__event__archived=False,
            prize__key_code=False,
            acceptcount__gt=F('acceptemailsentcount'),
            shippingstate='PENDING',
        )

    def shipped_email_pending(self):
        return self.filter(
            Q(shippingstate='SHIPPED') | Q(prize__requiresshipping=False),
            prize__event__archived=False,
            shippingemailsent=False,
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
    # also used for awarding non-physical prizes such as game keys
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
        choices=(('PENDING', 'Pending'), ('SHIPPED', 'Shipped')),
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
    def event(self):
        return self.prize.event

    @property
    def requiresshipping(self):
        return self.prize.requiresshipping

    @property
    def full(self):
        return (
            self.acceptcount + self.pendingcount + self.declinecount
            == self.prize.maxmultiwin
        )

    @property
    def accepted(self):
        return self.acceptcount > 0

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

    def check_multiwin(self, value):
        if value > self.prize.maxmultiwin:
            raise ValidationError(
                'Count must not exceed the prize multi win amount ({0})'.format(
                    self.prize.maxmultiwin
                )
            )
        return value

    def clean_pendingcount(self):
        return self.check_multiwin(self.pendingcount)

    def clean_acceptcount(self):
        return self.check_multiwin(self.acceptcount)

    def clean_declinecount(self):
        return self.check_multiwin(self.declinecount)

    def clean(self):
        errors = defaultdict(list)
        if (
            self.pendingcount + self.acceptcount + self.declinecount
            > self.prize.maxmultiwin
        ):
            errors[NON_FIELD_ERRORS].append(
                'Sum of counts must be at most the prize multi-win multiplicity'
            )
        agg = self.prize.claims.exclude(pk=self.pk).aggregate(
            accept=Coalesce(Sum('acceptcount'), 0),
            pending=Coalesce(Sum('pendingcount'), 0),
        )
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
                'Prize winners attached to key code prizes need a prize key attached as well.'
            )
        if errors:
            raise ValidationError(errors)

    def validate_unique(self, **kwargs):
        if (
            'winner' not in kwargs
            and 'prize' not in kwargs
            and self.prize.category is not None
        ):
            for prizeWon in PrizeClaim.objects.filter(
                prize__category=self.prize.category,
                winner=self.winner,
                prize__event=self.prize.event,
            ):
                if prizeWon.id != self.id:
                    raise ValidationError(
                        'Category, winner, and prize must be unique together'
                    )

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
