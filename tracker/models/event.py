import datetime
import decimal
import itertools
import logging
from decimal import Decimal

import post_office.models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_slug
from django.db import models
from django.db.models import Case, Count, F, Q, Sum, When, signals
from django.db.models.functions import Coalesce
from django.dispatch import receiver
from django.urls import reverse
from timezone_field import TimeZoneField

from tracker import compat, util
from tracker.validators import nonzero, positive

from .fields import TimestampField
from .util import LatestEvent

__all__ = [
    'Event',
    'PostbackURL',
    'SpeedRun',
    'Runner',
    'Submission',
    'Headset',
]

_currencyChoices = (('USD', 'US Dollars'), ('CAD', 'Canadian Dollars'))


logger = logging.getLogger(__name__)


class EventQuerySet(models.QuerySet):
    def current(self, timestamp=None):
        timestamp = timestamp or util.utcnow()
        runs = SpeedRun.objects.filter(starttime__lte=timestamp, endtime__gte=timestamp)
        if len(runs) == 1:
            return self.filter(pk=runs.first().event_id).first()
        else:
            if len(runs) > 1:
                logger.warning(
                    f'Timestamp {timestamp} returned multiple runs: {",".join(str(r.id) for r in runs)}'
                )
            return None

    def next(self, timestamp=None):
        timestamp = timestamp or util.utcnow()
        return self.filter(datetime__gt=timestamp).order_by('datetime').first()

    def current_or_next(self, timestamp=None):
        return self.current(timestamp) or self.next(timestamp)

    def with_annotations(self, ignore_order=False):
        annotated = self.annotate(
            amount=Coalesce(
                Sum(
                    Case(
                        When(
                            Q(donation__transactionstate='COMPLETED'),
                            then=F('donation__amount'),
                        ),
                        output_field=models.DecimalField(decimal_places=2),
                    )
                ),
                Decimal('0.00'),
            ),
            donation_count=Coalesce(
                Count('donation', filter=Q(donation__transactionstate='COMPLETED')), 0
            ),
        )

        if not ignore_order:
            annotated = annotated.order_by(*self.model._meta.ordering)

        return annotated


class EventManager(models.Manager):
    def get_by_natural_key(self, short):
        return self.get(short=short)


class Event(models.Model):
    objects = EventManager.from_queryset(EventQuerySet)()
    short = models.CharField(
        max_length=64,
        unique=True,
        help_text='This must be unique, as it is used for slugs.',
        validators=[validate_slug],
    )
    name = models.CharField(max_length=128)
    hashtag = models.CharField(
        max_length=32,
        help_text='Normally you can use the short id for this, but this value can override it.',
        blank=True,
    )
    use_one_step_screening = models.BooleanField(
        default=True,
        verbose_name='Use One-Step Screening',
        help_text='Turn this off if you use the "Head Donations" flow',
    )
    receivername = models.CharField(
        max_length=128, blank=True, null=False, verbose_name='Receiver Name'
    )
    receiver_short = models.CharField(
        max_length=16,
        blank=True,
        verbose_name='Receiver Name (Short)',
        help_text='Useful for space constrained displays',
    )
    targetamount = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        validators=[positive, nonzero],
        verbose_name='Target Amount',
        default=0,
    )
    minimumdonation = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        validators=[positive, nonzero],
        verbose_name='Minimum Donation',
        help_text='Enforces a minimum donation amount on the donate page.',
        default=decimal.Decimal('1.00'),
    )
    auto_approve_threshold = models.DecimalField(
        'Threshold amount to send to reader or ignore',
        decimal_places=2,
        max_digits=20,
        validators=[positive],
        blank=True,
        null=True,
        help_text='Leave blank to turn off auto-approval behavior. If set, anonymous, no-comment donations at or above this amount get sent to the reader. Below this amount, they are ignored.',
    )
    paypalemail = models.EmailField(
        max_length=128, null=False, blank=False, verbose_name='Receiver Paypal'
    )
    paypalcurrency = models.CharField(
        max_length=8,
        null=False,
        blank=False,
        default=_currencyChoices[0][0],
        choices=_currencyChoices,
        verbose_name='Currency',
    )
    paypalimgurl = models.CharField(
        max_length=1024,
        null=False,
        blank=True,
        verbose_name='Logo URL',
    )
    donationemailtemplate = models.ForeignKey(
        post_office.models.EmailTemplate,
        verbose_name='Donation Email Template',
        default=None,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='event_donation_templates',
    )
    pendingdonationemailtemplate = models.ForeignKey(
        post_office.models.EmailTemplate,
        verbose_name='Pending Donation Email Template',
        default=None,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='event_pending_donation_templates',
    )
    donationemailsender = models.EmailField(
        max_length=128, null=True, blank=True, verbose_name='Donation Email Sender'
    )
    scheduleid = models.CharField(
        max_length=128,
        unique=True,
        null=True,
        blank=True,
        verbose_name='Schedule ID (LEGACY)',
        editable=False,
    )
    datetime = models.DateTimeField()
    timezone = TimeZoneField(default='US/Eastern')
    locked = models.BooleanField(
        default=False,
        help_text='Requires special permission to edit this event or anything associated with it.',
    )
    allow_donations = models.BooleanField(
        default=True,
        help_text='Whether or not donations are open for this event. A locked event will override this setting.',
    )
    # Fields related to prize management
    prizecoordinator = models.ForeignKey(
        User,
        default=None,
        null=True,
        blank=True,
        verbose_name='Prize Coordinator',
        help_text='The person responsible for managing prize acceptance/distribution',
        on_delete=models.PROTECT,
    )
    allowed_prize_countries = models.ManyToManyField(
        'Country',
        blank=True,
        verbose_name='Allowed Prize Countries',
        help_text='List of countries whose residents are allowed to receive prizes (leave blank to allow all countries)',
    )
    disallowed_prize_regions = models.ManyToManyField(
        'CountryRegion',
        blank=True,
        verbose_name='Disallowed Regions',
        help_text='A blacklist of regions within allowed countries that are not allowed for drawings (e.g. Quebec in Canada)',
    )
    prize_accept_deadline_delta = models.IntegerField(
        default=14,
        null=False,
        blank=False,
        verbose_name='Prize Accept Deadline Delta',
        help_text='The number of days a winner will be given to accept a prize before it is re-rolled.',
        validators=[positive, nonzero],
    )
    prize_drawing_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Prize Drawing Date',
        help_text='Prizes will be eligible for drawing on or after this date, otherwise they will be eligible for drawing immediately after their window closes.',
    )
    prizecontributoremailtemplate = models.ForeignKey(
        post_office.models.EmailTemplate,
        default=None,
        null=True,
        blank=True,
        verbose_name='Prize Contributor Accept/Deny Email Template',
        help_text="Email template to use when responding to prize contributor's submission requests",
        related_name='event_prizecontributortemplates',
        on_delete=models.SET_NULL,
    )
    prizewinneremailtemplate = models.ForeignKey(
        post_office.models.EmailTemplate,
        default=None,
        null=True,
        blank=True,
        verbose_name='Prize Winner Email Template',
        help_text='Email template to use when someone wins a prize.',
        related_name='event_prizewinnertemplates',
        on_delete=models.SET_NULL,
    )
    prizewinneracceptemailtemplate = models.ForeignKey(
        post_office.models.EmailTemplate,
        default=None,
        null=True,
        blank=True,
        verbose_name='Prize Accepted Email Template',
        help_text='Email template to use when someone accepts a prize (and thus it needs to be shipped).',
        related_name='event_prizewinneraccepttemplates',
        on_delete=models.SET_NULL,
    )
    prizeshippedemailtemplate = models.ForeignKey(
        post_office.models.EmailTemplate,
        default=None,
        null=True,
        blank=True,
        verbose_name='Prize Shipped Email Template',
        help_text='Email template to use when the aprize has been shipped to its recipient).',
        related_name='event_prizeshippedtemplates',
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        return self.name

    # used for templates
    def next(self):
        return (
            Event.objects.filter(datetime__gte=self.datetime)
            .order_by('datetime')
            .exclude(pk=self.pk)
            .first()
        )

    def prev(self):
        return (
            Event.objects.filter(datetime__lte=self.datetime)
            .order_by('datetime')
            .exclude(pk=self.pk)
            .last()
        )

    def get_absolute_url(self):
        return reverse('tracker:index', args=(self.id,))

    def natural_key(self):
        return (self.short,)

    def save(self, *args, **kwargs):
        if self.datetime is not None:
            if (
                self.datetime.tzinfo is None
                or self.datetime.tzinfo.utcoffset(self.datetime) is None
            ):
                self.datetime = self.datetime.replace(tzinfo=self.timezone)
        super(Event, self).save(*args, **kwargs)

        # one side of an event setting edge case, see Donation.save() for the other
        if self.use_one_step_screening:
            # TODO: send notifications?
            self.donation_set.completed().to_approve().update(readstate='READY')
        first_run = self.speedrun_set.all().first()
        if first_run and first_run.starttime and first_run.starttime != self.datetime:
            first_run.save(fix_time=True)

    def clean(self):
        if self.id and self.id < 1:
            raise ValidationError('Event ID must be positive and non-zero')
        if not self.scheduleid:
            self.scheduleid = None
        if (
            self.donationemailtemplate is not None
            or self.pendingdonationemailtemplate is not None
        ):
            if not self.donationemailsender:
                raise ValidationError(
                    'Must specify a donation email sender if automailing is used'
                )
        if (
            self.prize_drawing_date
            and self.speedrun_set.last().end_time >= self.prize_drawing_date
        ):
            raise ValidationError(
                {'prise_drawing_date': 'Draw date must be after the last run'}
            )

    @property
    def date(self):
        return self.datetime.date()

    class Meta:
        app_label = 'tracker'
        get_latest_by = 'datetime'
        permissions = (('can_edit_locked_events', 'Can edit locked events'),)
        ordering = ('-datetime',)


class PostbackURL(models.Model):
    event = models.ForeignKey(
        'Event',
        on_delete=models.PROTECT,
        verbose_name='Event',
        null=False,
        blank=False,
        related_name='postbacks',
    )
    url = models.URLField(blank=False, null=False, verbose_name='URL')

    class Meta:
        app_label = 'tracker'


class RunTagManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name.lower())

    def get_or_create_by_natural_key(self, name):
        return self.get_or_create(name=name.lower())


class RunTag(models.Model):
    name = models.CharField(
        unique=True,
        max_length=32,
        error_messages={'unique': 'Tags must be case-insensitively unique.'},
    )
    objects = RunTagManager()

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude)
        exclude = exclude or []
        if (
            'name' not in exclude
            and RunTag.objects.exclude(id=self.id)
            .filter(name=self.name.lower())
            .exists()
        ):
            raise ValidationError({'name': self.unique_error_message(RunTag, ['name'])})

    def save(self, *args, **kwargs):
        self.name = self.name.lower()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


_DEFAULT_RUN_MIN = 3
_DEFAULT_RUN_MAX = 7
_DEFAULT_RUN_DELTA = datetime.timedelta(hours=12)


class SpeedRunQueryset(models.QuerySet):
    def upcoming(
        self,
        *,
        include_current=True,
        min_runs=_DEFAULT_RUN_MIN,
        max_runs=_DEFAULT_RUN_MAX,
        delta=_DEFAULT_RUN_DELTA,
        now=None,
    ):
        queryset = self
        if now is None:
            now = util.utcnow()
        elif isinstance(now, str):
            now = datetime.datetime.fromisoformat(now)
        elif isinstance(now, datetime.datetime):
            pass  # no adjustment necessary
        else:
            raise ValueError(f'Expected None, str, or datetime, got {type(now)}')
        if include_current:
            queryset = queryset.filter(endtime__gte=now)
        else:
            queryset = queryset.filter(starttime__gte=now)
        if delta:
            high_filter = queryset.filter(endtime__lte=now + delta)
        else:
            high_filter = queryset
        count = high_filter.count()
        if max_runs is not None and count > max_runs:
            queryset = queryset[:max_runs]
        elif min_runs is not None and count < min_runs:
            queryset = queryset[:min_runs]
        else:
            queryset = high_filter
        return queryset


class SpeedRunManager(models.Manager):
    def get_by_natural_key(self, name, event):
        return self.get(name=name, event=Event.objects.get_by_natural_key(*event))

    def get_or_create_by_natural_key(self, name, event):
        return self.get_or_create(
            name=name, event=Event.objects.get_by_natural_key(*event)
        )


def runners_exists(runners):
    for r in runners.split(','):
        try:
            Runner.objects.get_by_natural_key(r.strip())
        except Runner.DoesNotExist:
            raise ValidationError('Runner not found: "%s"' % r.strip())


class SpeedRun(models.Model):
    objects = SpeedRunManager.from_queryset(SpeedRunQueryset)()
    event = models.ForeignKey('Event', on_delete=models.PROTECT, default=LatestEvent)
    name = models.CharField(max_length=64)
    display_name = models.TextField(
        max_length=256,
        blank=True,
        verbose_name='Display Name',
        help_text='How to display this game on the stream.',
    )
    twitch_name = models.TextField(
        max_length=256,
        blank=True,
        verbose_name='Twitch Name',
        help_text='What game name to use on Twitch',
    )
    # This field is now deprecated, we should eventually set up a way to migrate the old set-up to use the donor links
    deprecated_runners = models.CharField(
        max_length=1024,
        blank=True,
        verbose_name='*DEPRECATED* Runners',
        editable=False,
        validators=[runners_exists],
    )
    console = models.CharField(max_length=32, blank=True)
    description = models.TextField(max_length=1024, blank=True)
    starttime = models.DateTimeField(
        verbose_name='Start Time', editable=False, null=True
    )
    endtime = models.DateTimeField(verbose_name='End Time', editable=False, null=True)
    # can be temporarily null when moving runs around, or null when they haven't been slotted in yet
    order = models.IntegerField(
        blank=True,
        null=True,
        help_text='Please note that using the schedule editor is much easier',
        validators=[positive],
    )
    anchor_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text="If set, will adjust the previous run to ensure this run's start time is always this value, or throw a validation error if it is not possible",
    )
    run_time = TimestampField(always_show_h=True)
    setup_time = TimestampField(always_show_h=True)
    runners = models.ManyToManyField('Runner')
    hosts = models.ManyToManyField('Headset', related_name='hosting_for', blank=True)
    commentators = models.ManyToManyField(
        'Headset', related_name='commentating_for', blank=True
    )
    coop = models.BooleanField(
        default=False,
        help_text='Cooperative runs should be marked with this for layout purposes',
    )
    onsite = models.CharField(
        max_length=6,
        default='ONSITE',
        choices=[('ONSITE', 'Onsite'), ('ONLINE', 'Online'), ('HYBRID', 'Hybrid')],
    )
    category = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text='The type of run being performed',
    )
    release_year = models.IntegerField(
        blank=True,
        null=True,
        verbose_name='Release Year',
        help_text='The year the game was released',
    )
    giantbomb_id = models.IntegerField(
        blank=True,
        null=True,
        verbose_name='GiantBomb Database ID',
        help_text='Identifies the game in the GiantBomb database, to allow auto-population of game data.',
    )
    tech_notes = models.TextField(blank=True, help_text='Notes for the tech crew')
    layout = models.CharField(
        blank=True, max_length=64, help_text='Which OBS layout to use'
    )
    priority_tag = models.ForeignKey(
        'RunTag',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='priority_runs',
    )
    tags = models.ManyToManyField('RunTag', blank=True, related_name='runs')

    class Meta:
        app_label = 'tracker'
        verbose_name = 'Speed Run'
        unique_together = (('name', 'category', 'event'), ('event', 'order'))
        ordering = ['event__datetime', 'order']
        permissions = (('can_view_tech_notes', 'Can view tech notes'),)

    def get_absolute_url(self):
        return reverse('tracker:run', args=(self.id,))

    def natural_key(self):
        return self.name, self.event.natural_key()

    @property
    def run_time_ms(self):
        return TimestampField.time_string_to_int(self.run_time)

    @property
    def setup_time_ms(self):
        return TimestampField.time_string_to_int(self.setup_time)

    @property
    def start_time_utc(self):
        return self.starttime.astimezone(datetime.timezone.utc)

    @property
    def end_time_utc(self):
        return self.endtime.astimezone(datetime.timezone.utc)

    def clean(self):
        if not self.name:
            raise ValidationError('Name cannot be blank')
        if not self.display_name:
            self.display_name = self.name
        if self.order:
            prev = (
                SpeedRun.objects.filter(order__lt=self.order, event=self.event)
                .exclude(pk=self.pk)
                .last()
            )
            next_anchor = (
                SpeedRun.objects.filter(order__gte=self.order, event=self.event)
                .exclude(anchor_time=None)
                .exclude(pk=self.pk)
                .first()
            )
            if prev:
                self.starttime = prev.endtime
            else:
                self.starttime = self.event.datetime
            if next_anchor:
                if self.anchor_time and next_anchor.anchor_time < self.anchor_time:
                    raise ValidationError(
                        {
                            'order': 'Next anchor in the order would occur before this one'
                        }
                    )
                for c, n in compat.pairwise(
                    itertools.chain(
                        [self],
                        SpeedRun.objects.filter(
                            event=self.event,
                            order__gt=self.order,
                            order__lte=next_anchor.order,
                        ).exclude(pk=self.pk),
                    )
                ):
                    if n.anchor_time:
                        if (
                            c.starttime + datetime.timedelta(milliseconds=c.run_time_ms)
                            > n.anchor_time
                        ):
                            raise ValidationError(
                                {
                                    'setup_time': 'Not enough available drift for next anchor time'
                                }
                            )
                    else:
                        n.starttime = c.starttime + datetime.timedelta(
                            milliseconds=c.run_time_ms + c.setup_time_ms
                        )
            if self.anchor_time:
                if not prev:
                    raise ValidationError(
                        {
                            'anchor_time': 'Cannot set anchor time for first run in an event'
                        }
                    )
                if (
                    prev.starttime + datetime.timedelta(milliseconds=prev.run_time_ms)
                    > self.anchor_time
                ):
                    raise ValidationError(
                        {
                            'anchor_time': 'Previous run does not have enough drift available for anchor time'
                        }
                    )
                self.starttime = self.anchor_time
        else:
            self.order = None

    def save(self, fix_time=True, fix_runners=True, *args, **kwargs):
        if self.priority_tag:
            self.tags.add(self.priority_tag)

        can_fix_time = self.order is not None and (
            self.run_time_ms != 0 or self.setup_time_ms != 0
        )

        # FIXME: better way to force normalization?

        self.run_time = self._meta.get_field('run_time').to_python(self.run_time)
        self.setup_time = self._meta.get_field('setup_time').to_python(self.setup_time)

        if self.order:
            prev_run = (
                SpeedRun.objects.filter(event=self.event, order__lt=self.order)
                .exclude(pk=self.pk)
                .last()
            )
            next_run = (
                SpeedRun.objects.filter(event=self.event, order__gt=self.order)
                .exclude(pk=self.pk)
                .first()
            )
        else:
            prev_run = next_run = None

        # fix our own time
        if fix_time and can_fix_time:
            if prev_run:
                if self.anchor_time:
                    self.starttime = self.anchor_time
                else:
                    self.starttime = prev_run.starttime + datetime.timedelta(
                        milliseconds=prev_run.run_time_ms + prev_run.setup_time_ms
                    )
            else:
                self.starttime = self.event.datetime
            if next_run and next_run.anchor_time:
                self.setup_time = (
                    next_run.anchor_time
                    - self.starttime
                    - datetime.timedelta(milliseconds=self.run_time_ms)
                )
            self.endtime = self.starttime + datetime.timedelta(
                milliseconds=self.run_time_ms + self.setup_time_ms
            )

        if fix_runners and self.id:
            self.deprecated_runners = ', '.join(
                sorted(str(r) for r in self.runners.all())
            )

        # TODO: strip out force_insert and force_delete? causes issues if you try to insert a run in the middle
        # with #create with an order parameter, but nobody should be doing that outside of tests anyway?
        # maybe the admin lets you do it...
        super(SpeedRun, self).save(*args, **kwargs)

        # fix up all the others if requested
        if fix_time:
            if prev_run and self.anchor_time:
                prev_kwargs = {
                    k: v for k, v in kwargs.items() if not k.startswith('force')
                }
                prev_run.save(*args, **prev_kwargs)
            if can_fix_time:
                if next_run:
                    if next_run.anchor_time:
                        return [self, next_run]
                    else:
                        starttime = self.starttime + datetime.timedelta(
                            milliseconds=self.run_time_ms + self.setup_time_ms
                        )
                        if next_run.starttime != starttime:
                            return [self] + next_run.save(*args, **kwargs)
            elif self.starttime:
                prev_run = (
                    SpeedRun.objects.filter(
                        event=self.event, starttime__lte=self.starttime
                    )
                    .exclude(order=None)
                    .exclude(pk=self.pk)
                    .last()
                )
                if prev_run:
                    self.starttime = prev_run.starttime + datetime.timedelta(
                        milliseconds=prev_run.run_time_ms + prev_run.setup_time_ms
                    )
                else:
                    self.starttime = self.event.datetime
                next_run = (
                    SpeedRun.objects.filter(
                        event=self.event, starttime__gte=self.starttime
                    )
                    .exclude(order=None)
                    .exclude(pk=self.pk)
                    .first()
                )
                if next_run and next_run.starttime != self.starttime:
                    return [self] + next_run.save(*args, **kwargs)
        return [self]

    def name_with_category(self):
        category_string = f' {self.category}' if self.category else ''
        return f'{self.name}{category_string}'

    def __str__(self):
        return f'{self.name_with_category()} (event_id: {self.event_id})'


class Runner(models.Model):
    class _Manager(models.Manager):
        def get_by_natural_key(self, name):
            return self.get(name__iexact=name)

        def get_or_create_by_natural_key(self, name):
            return self.get_or_create(name__iexact=name, defaults={'name': name})

    class Meta:
        app_label = 'tracker'

    objects = _Manager()
    name = models.CharField(
        max_length=64,
        unique=True,
        error_messages={
            'unique': 'Runner with this case-insensitive Name already exists.'
        },
    )
    stream = models.URLField(max_length=128, blank=True)
    twitter = models.SlugField(max_length=15, blank=True)
    youtube = models.SlugField(max_length=20, blank=True)
    platform = models.CharField(
        max_length=20,
        default='TWITCH',
        choices=(
            ('TWITCH', 'Twitch'),
            ('MIXER', 'Mixer'),
            ('FACEBOOK', 'Facebook'),
            ('YOUTUBE', 'Youtube'),
        ),
        help_text='Streaming Platforms',
    )
    pronouns = models.CharField(max_length=20, blank=True, help_text='They/Them')
    donor = models.OneToOneField(
        'tracker.Donor', blank=True, null=True, on_delete=models.SET_NULL
    )

    def validate_unique(self, exclude=None):
        case_insensitive = Runner.objects.filter(name__iexact=self.name)
        if self.id:
            case_insensitive = case_insensitive.exclude(id=self.id)
        case_insensitive = case_insensitive.exists()
        try:
            super(Runner, self).validate_unique(exclude)
        except ValidationError as e:
            if case_insensitive:
                e.error_dict.setdefault('name', []).append(
                    self.unique_error_message(Runner, ['name'])
                )
            raise
        if case_insensitive:
            raise self.unique_error_message(Runner, ['name'])

    def natural_key(self):
        return (self.name,)

    def __str__(self):
        return self.name


# XXX: this signal handler will run for both SpeedRuns and Runners
@receiver(signals.m2m_changed, sender=SpeedRun.runners.through)
def runners_changed(sender, instance, action, model, pk_set, reverse, using, **kwargs):
    if action[:4] == 'post':
        if reverse:
            instances = model.objects.using(using).filter(pk__in=pk_set)
        else:
            instances = [instance]
        for instance in instances:
            instance.save()


class Submission(models.Model):
    class Meta:
        app_label = 'tracker'

    external_id = models.IntegerField(primary_key=True)
    run = models.ForeignKey('SpeedRun', on_delete=models.CASCADE)
    runner = models.ForeignKey('Runner', on_delete=models.CASCADE)
    game_name = models.CharField(max_length=64)
    category = models.CharField(max_length=64)
    console = models.CharField(max_length=32)
    estimate = TimestampField(always_show_h=True)

    def __str__(self):
        return f'{self.game_name} ({self.category}) by {self.runner}'

    def save(self, *args, **kwargs):
        super(Submission, self).save(*args, **kwargs)
        ret = [self]
        save_run = False
        if not self.run.category:
            self.run.category = self.category
            save_run = True
        if not self.run.description:
            self.run.description = self.category
            save_run = True
        if not self.run.console:
            self.run.console = self.console
            save_run = True
        if not self.run.run_time:
            self.run.run_time = self.estimate
            save_run = True
        if save_run:
            self.run.save()
            ret.append(self.run)
        return ret


class Headset(models.Model):
    class _Manager(models.Manager):
        def get_by_natural_key(self, name):
            return self.get(name__iexact=name)

    class Meta:
        ordering = ('name',)

    objects = _Manager()
    name = models.CharField(
        max_length=64,
        unique=True,
        error_messages={
            'unique': 'Headset with this case-insensitive Name already exists.'
        },
    )
    pronouns = models.CharField(
        max_length=20, blank=True, help_text='Example: They/Them'
    )
    runner = models.OneToOneField(
        'Runner',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text='Optional Runner link',
    )

    def __str__(self):
        return self.name

    def validate_unique(self, exclude=None):
        case_insensitive = Headset.objects.filter(name__iexact=self.name)
        if self.id:
            case_insensitive = case_insensitive.exclude(id=self.id)
        case_insensitive = case_insensitive.exists()
        try:
            super(Headset, self).validate_unique(exclude)
        except ValidationError as e:
            if case_insensitive:
                # FIXME: does this actually work?
                e.error_dict.setdefault('name', []).append(
                    self.unique_error_message(Headset, ['name'])
                )
            raise
        if case_insensitive:
            raise self.unique_error_message(Headset, ['name'])

    def natural_key(self):
        return (self.name,)


class VideoLinkType(models.Model):
    name = models.CharField(max_length=32, unique=True)

    def __str__(self):
        return self.name


class VideoLink(models.Model):
    run = models.ForeignKey(
        SpeedRun, on_delete=models.PROTECT, related_name='video_links'
    )
    link_type = models.ForeignKey(VideoLinkType, on_delete=models.PROTECT)
    url = models.URLField()
    # public = models.BooleanField(default=True) # TODO: add this once I figure out how to filter nested serializers

    def __str__(self):
        return f'{self.run} -- {self.link_type} -- {self.url}'

    class Meta:
        unique_together = ('run', 'link_type')
