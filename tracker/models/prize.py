import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models
from django.db.models import Q, Sum
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
    'PrizeWinner',
    'PrizeCategory',
    'DonorPrizeEntry',
]

USER_MODEL_NAME = getattr(settings, 'AUTH_USER_MODEL', User)


class PrizeQuerySet(models.QuerySet):
    PUBLIC_FEEDS = ('public', 'current')
    HIDDEN_FEEDS = ('to_draw', 'pending', 'all')
    ALL_FEEDS = PUBLIC_FEEDS + HIDDEN_FEEDS

    def public(self):
        return self.filter(state='ACCEPTED')

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
            Q(prizewinner__isnull=True)
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
                Q(prizewinner=None)
                | (
                    Q(prizewinner__pendingcount__gt=0)
                    & Q(prizewinner__acceptdeadline__lt=time)
                )
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


class PrizeManager(models.Manager):
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
        default=Decimal('5.00'),
        verbose_name='Maximum Bid',
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
                'Cannot create prizes without a TRACKER_SWEEPSTAKES_URL in settings'
            )
        if self.maxmultiwin > 1 and self.category is not None:
            raise ValidationError(
                {
                    'maxmultiwin': 'A donor may not win more than one prize of any category, so setting a prize '
                    'to have multiple wins per single donor with a non-null category is incompatible.'
                }
            )
        if (not self.startrun) != (not self.endrun):
            raise ValidationError(
                {'startrun': 'Must have both Start Run and End Run set, or neither.'}
            )
        if self.startrun and self.event != self.startrun.event:
            raise ValidationError(
                {'event': 'Prize Event must be the same as Start Run Event'}
            )
        if self.endrun and self.event != self.endrun.event:
            raise ValidationError(
                {'event': 'Prize Event must be the same as End Run Event'}
            )
        if self.startrun and self.startrun.starttime > self.endrun.starttime:
            raise ValidationError(
                {'startrun': 'Start Run must begin sooner than End Run'}
            )
        if (not self.starttime) != (not self.endtime):
            raise ValidationError(
                {'starttime': 'Must have both Start Time and End Time set, or neither'}
            )
        if self.starttime and self.starttime > self.endtime:
            raise ValidationError(
                {'starttime': 'Prize Start Time must be later than End Time'}
            )
        if self.startrun and self.starttime:
            raise ValidationError(
                {'starttime': 'Cannot have both Start/End Run and Start/End Time set'}
            )

    def save(self, *args, **kwargs):
        if not settings.TRACKER_SWEEPSTAKES_URL:
            raise ImproperlyConfigured(
                'Cannot create prizes without a TRACKER_SWEEPSTAKES_URL in settings'
            )

        using = kwargs.get('using', None)
        self.maximumbid = self.minimumbid
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
        super(Prize, self).save(*args, **kwargs)

    def eligible_donors(self):
        donationSet = Donation.objects.filter(
            event=self.event, transactionstate='COMPLETED'
        ).select_related('donor')
        # remove all donations from donors who have won a prize under the same category for this event
        if self.category is not None:
            donationSet = donationSet.exclude(
                Q(
                    donor__prizewinner__prize__category=self.category,
                    donor__prizewinner__prize__event=self.event,
                )
            )

        # Apply the country/region filter to the drawing
        if self.custom_country_filter:
            countryFilter = self.allowed_prize_countries.all()
            regionBlacklist = self.disallowed_prize_regions.all()
        else:
            countryFilter = self.event.allowed_prize_countries.all()
            regionBlacklist = self.event.disallowed_prize_regions.all()

        if countryFilter.exists():
            donationSet = donationSet.filter(donor__addresscountry__in=countryFilter)
        if regionBlacklist.exists():
            for region in regionBlacklist:
                donationSet = donationSet.exclude(
                    donor__addresscountry=region.country,
                    donor__addressstate__iexact=region.name,
                )

        fullDonors = PrizeWinner.objects.filter(prize=self, sumcount=self.maxmultiwin)
        donationSet = donationSet.exclude(donor__in=[w.winner for w in fullDonors])
        if self.has_draw_time():
            donationSet = donationSet.filter(
                timereceived__gte=self.start_draw_time(),
                timereceived__lte=self.end_draw_time(),
            )
        donors = {}
        for donation in donationSet:
            if self.sumdonations:
                donors.setdefault(donation.donor, Decimal('0.0'))
                donors[donation.donor] += donation.amount
            else:
                donors[donation.donor] = max(
                    donation.amount, donors.get(donation.donor, Decimal('0.0'))
                )
        directEntries = DonorPrizeEntry.objects.filter(prize=self).exclude(
            donor__in=[w.winner for w in fullDonors]
        )
        for entry in directEntries:
            donors.setdefault(entry.donor, Decimal('0.0'))
            donors[entry.donor] = max(
                entry.weight * self.minimumbid, donors[entry.donor]
            )
            if self.maximumbid:
                donors[entry.donor] = min(donors[entry.donor], self.maximumbid)
        if not donors:
            return []
        elif self.randomdraw:

            def weight(mn, mx, a):
                if mx is not None and a > mx:
                    return float(mx / mn)
                return float(a / mn)

            return sorted(
                [
                    {
                        'donor': d[0].id,
                        'amount': d[1],
                        'weight': weight(self.minimumbid, self.maximumbid, d[1]),
                    }
                    for d in donors.items()
                    if self.minimumbid <= d[1]
                ],
                key=lambda d: d['donor'],
            )

        else:
            m = max(donors.items(), key=lambda d: d[1])
            return [{'donor': m[0].id, 'amount': m[1], 'weight': 1.0}]

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

    def games_based_drawing(self):
        return self.startrun and self.endrun

    def games_range(self):
        if self.games_based_drawing():
            # TODO: fix me to use order... is this even used at all outside of tests?
            return SpeedRun.objects.filter(
                event=self.event,
                starttime__gte=self.startrun.starttime,
                endtime__lte=self.endrun.endtime,
            )
        else:
            return SpeedRun.objects.none()

    def has_draw_time(self):
        return self.start_draw_time() and self.end_draw_time()

    def start_draw_time(self):
        if self.startrun and self.startrun.order:
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
        if self.endrun and self.endrun.order:
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
            [
                x
                for x in self.get_prize_winners()
                .aggregate(Sum('pendingcount'), Sum('acceptcount'))
                .values()
                if x is not None
            ]
        )

    def maxed_winners(self):
        return self.current_win_count() == self.maxwinners

    def get_prize_winners(self, time=None):
        time = time or util.utcnow()
        return self.prizewinner_set.filter(
            Q(acceptcount__gt=0)
            | (
                Q(pendingcount__gt=0)
                & (Q(acceptdeadline=None) | Q(acceptdeadline__gt=time))
            )
        )

    def get_expired_winners(self, time=None):
        time = time or util.utcnow()
        return self.prizewinner_set.filter(pendingcount__gt=0, acceptdeadline__lt=time)

    def get_accepted_winners(self):
        return self.prizewinner_set.filter(Q(acceptcount__gt=0))

    def has_accepted_winners(self):
        return self.get_accepted_winners().exists()

    def is_pending_shipping(self):
        return self.get_accepted_winners().filter(Q(shippingstate='PENDING')).exists()

    def is_fully_shipped(self):
        return self.maxed_winners() and not self.is_pending_shipping()

    def get_prize_winner(self):
        if self.maxwinners == 1:
            return self.get_prize_winners().first()
        else:
            raise Exception('Cannot get single winner for multi-winner prize')

    def get_winners(self):
        return [w.winner for w in self.get_prize_winners()]

    def get_winner(self):
        prizeWinner = self.get_prize_winner()
        if prizeWinner:
            return prizeWinner.winner
        else:
            return None


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
    prize = models.ForeignKey('Prize', on_delete=models.PROTECT)
    prize_winner = models.OneToOneField(
        'PrizeWinner', on_delete=models.PROTECT, null=True, blank=True
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

    @property
    def winner(self):
        return self.prize_winner_id and self.prize_winner.winner

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
        raise Exception('insanity')
    count = prize.prizekey_set.count()
    changed = False
    if prize.maxwinners != count:
        prize.maxwinners = count
        changed = True
    if prize.maxmultiwin != 1:
        prize.maxmultiwin = 1
        changed = True
    if changed:
        prize.save()


class PrizeWinnerQuerySet(models.QuerySet):
    def claimed(self):
        return self.filter(acceptcount__gt=0)

    def pending(self):
        return self.filter(
            Q(pendingcount__gt=0)
            & (Q(acceptdeadline=None) | Q(acceptdeadline__gt=util.utcnow()))
        )

    def claimed_or_pending(self):
        return self.claimed() | self.pending()


class PrizeWinner(models.Model):
    objects = models.Manager.from_queryset(PrizeWinnerQuerySet)()
    winner = models.ForeignKey(
        'Donor', null=False, blank=False, on_delete=models.PROTECT
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
        help_text='The number of copied this winner has won and accepted.',
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
    sumcount = models.IntegerField(
        default=1,
        null=False,
        blank=False,
        editable=False,
        validators=[positive],
        verbose_name='Sum Counts',
        help_text='The total number of prize instances associated with this winner',
    )
    prize = models.ForeignKey(
        'Prize', null=False, blank=False, on_delete=models.PROTECT
    )
    emailsent = models.BooleanField(
        default=False, verbose_name='Notification Email Sent'
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
        verbose_name = 'Prize Winner'
        unique_together = (
            'prize',
            'winner',
        )

    def make_winner_url(self):
        import warnings

        warnings.warn(
            '`make_winner_url` is deprecated, please use `claim_url` instead',
            DeprecationWarning,
        )
        return self.claim_url

    def create_claim_url(self, request):
        self._claim_url = request.build_absolute_uri(
            util.build_public_url(
                reverse('tracker:prize_winner', args=(self.pk,))
                + f'?auth_code={self.auth_code}'
            )
        )

    @property
    def claim_url(self):
        if not hasattr(self, '_claim_url'):
            raise AttributeError(
                'you must call `create_claim_url` with the proper request before retrieving this property'
            )
        return self._claim_url

    @property
    def donor_cache(self):
        # accounts for people who mail-in entry and never donated
        return self.winner.cache_for(self.prize.event_id) or self.winner

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
        self.sumcount = self.pendingcount + self.acceptcount + self.declinecount
        if self.sumcount == 0:
            raise ValidationError('Sum of counts must be greater than zero')
        if self.sumcount > self.prize.maxmultiwin:
            raise ValidationError(
                'Sum of counts must be at most the prize multi-win multiplicity'
            )
        prizeSum = self.acceptcount + self.pendingcount
        for winner in self.prize.prizewinner_set.exclude(pk=self.pk):
            prizeSum += winner.acceptcount + winner.pendingcount
        if prizeSum > self.prize.maxwinners:
            raise ValidationError(
                'Number of prize winners is greater than the maximum for this prize.'
            )
        if self.trackingnumber and not self.couriername:
            raise ValidationError(
                'A tracking number is only useful with a courier name as well!'
            )
        if self.winner and self.acceptcount > 0 and self.prize.requiresshipping:
            if not self.prize.is_country_region_allowed(
                self.winner.addresscountry, self.winner.addressstate
            ):
                message = 'Unfortunately, for legal or logistical reasons, we cannot ship this prize to that region. Please accept our deepest apologies.'
                coordinator = self.prize.event.prizecoordinator
                if coordinator:
                    message += ' If you have any questions, please contact our prize coordinator at {0}'.format(
                        coordinator.email
                    )
                raise ValidationError(message)
        if self.prize.key_code and not hasattr(self, 'prize_key'):
            raise ValidationError(
                'Prize winners attached to key code prizes need a prize key attached as well.'
            )

    def validate_unique(self, **kwargs):
        if (
            'winner' not in kwargs
            and 'prize' not in kwargs
            and self.prize.category is not None
        ):
            for prizeWon in PrizeWinner.objects.filter(
                prize__category=self.prize.category,
                winner=self.winner,
                prize__event=self.prize.event,
            ):
                if prizeWon.id != self.id:
                    raise ValidationError(
                        'Category, winner, and prize must be unique together'
                    )

    def save(self, *args, **kwargs):
        self.sumcount = self.pendingcount + self.acceptcount + self.declinecount
        super(PrizeWinner, self).save(*args, **kwargs)

    @property
    def event(self):
        return self.prize.event

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
    donor = models.ForeignKey(
        'Donor', null=False, blank=False, on_delete=models.PROTECT
    )
    prize = models.ForeignKey(
        'Prize', null=False, blank=False, on_delete=models.PROTECT
    )
    weight = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        default=Decimal('1.0'),
        verbose_name='Entry Weight',
        validators=[positive, nonzero],
        help_text='This is the weight to apply this entry in the drawing (if weight is applicable).',
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
