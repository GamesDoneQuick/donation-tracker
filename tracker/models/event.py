import decimal
import re

import post_office.models
import pytz
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_slug
from django.db import models
from django.db.models import signals
from django.dispatch import receiver
from django.urls import reverse
from timezone_field import TimeZoneField

from tracker.signals import model_changed
from tracker.validators import positive, nonzero
from .fields import TimestampField, Duration
from .util import LatestEvent

__all__ = [
    'Event',
    'PostbackURL',
    'SpeedRun',
    'Runner',
    'Submission',
]

_timezoneChoices = [(x, x) for x in pytz.common_timezones]
_currencyChoices = (('USD', 'US Dollars'), ('CAD', 'Canadian Dollars'))


class EventManager(models.Manager):
    def get_by_natural_key(self, short):
        return self.get(short=short)


class Event(models.Model):
    objects = EventManager()
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
        max_length=1024, null=False, blank=True, verbose_name='Logo URL',
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

    def next(self):
        return (
            Event.objects.filter(datetime__gte=self.datetime)
            .exclude(pk=self.pk)
            .first()
        )

    def prev(self):
        return (
            Event.objects.filter(datetime__lte=self.datetime).exclude(pk=self.pk).last()
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
                self.datetime = self.timezone.localize(self.datetime)
        super(Event, self).save(*args, **kwargs)

        # When an event's datetime moves later than the starttime of the first
        # run, we need to trigger a save on the run to update all runs' times
        # properly to begin after the event starts.
        first_run = self.speedrun_set.all().first()
        if first_run and first_run.starttime and first_run.starttime != self.datetime:
            first_run.save(fix_time=True)

    def clean(self):
        if self.id and self.id < 1:
            raise ValidationError('Event ID must be positive and non-zero')
        if not re.match(r'^\w+$', self.short):
            raise ValidationError('Event short name must be a url-safe string')
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

    @property
    def date(self):
        return self.datetime.date()

    class Meta:
        app_label = 'tracker'
        get_latest_by = 'datetime'
        permissions = (('can_edit_locked_events', 'Can edit locked events'),)
        ordering = ('datetime',)


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
    objects = SpeedRunManager()
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
    commentators = models.CharField(max_length=1024, blank=True)
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
    run_time = TimestampField(always_show_h=True, blank=True)
    setup_time = TimestampField(always_show_h=True, blank=True)
    runners = models.ManyToManyField('Runner')
    coop = models.BooleanField(
        default=False,
        help_text='Cooperative runs should be marked with this for layout purposes',
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
    def total_length(self):
        return Duration(self.run_time) + Duration(self.setup_time)

    def clean(self):
        if not self.name:
            raise ValidationError('Name cannot be blank')
        if not self.display_name:
            self.display_name = self.name
        if not self.order:
            self.order = None
        if self.order and not self.total_length:
            raise ValidationError(
                'At least one length field must be set if order is set'
            )

    def save(self, fix_time=True, fix_runners=True, *args, **kwargs):
        self.run_time = Duration(self.run_time)
        self.setup_time = Duration(self.setup_time)

        old_starttime = self.starttime

        if not self.order:
            self.starttime = self.endtime = None

        # fix our own time
        if fix_time and self.order:
            prev_run = SpeedRun.objects.filter(
                event=self.event, order__lt=self.order
            ).last()
            if prev_run:
                self.starttime = prev_run.starttime + prev_run.total_length
            else:
                self.starttime = self.event.datetime
            self.endtime = self.starttime + self.total_length

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
            if self.order:
                next_run = SpeedRun.objects.filter(
                    event=self.event, order__gt=self.order
                ).first()
                starttime = self.starttime + self.total_length
                if next_run and next_run.starttime != starttime:
                    return [self] + next_run.save(*args, **kwargs)
            elif old_starttime:
                # our order just changed to null
                prev_run = (
                    SpeedRun.objects.filter(
                        event=self.event, starttime__lte=old_starttime
                    )
                    .exclude(order=None)
                    .last()
                )
                if prev_run:
                    next_starttime = old_starttime + prev_run.total_length
                else:
                    next_starttime = self.event.datetime
                next_run = (
                    SpeedRun.objects.filter(
                        event=self.event, starttime__gte=next_starttime
                    )
                    .exclude(order=None)
                    .first()
                )
                if next_run and next_run.starttime != next_starttime:
                    return [self] + next_run.save(*args, **kwargs)
        return [self]

    def name_with_category(self):
        category_string = f' {self.category}' if self.category else ''
        return f'{self.name}{category_string}'

    def __str__(self):
        return f'{self.name_with_category()} (event_id: {self.event_id})'


@receiver(model_changed, sender=SpeedRun)
def adjust_times(sender, instance, **kwargs):
    old, new = instance
    if not old.order:
        return {}

    if old.total_length != new.total_length:
        delta = new.total_length - old.total_length
    else:
        return {}

    runs = SpeedRun.objects.filter(event=old.event, order__gt=old.order).exclude(
        run_time=0
    )

    def make_callback(run):
        def callback():
            run.starttime = run.starttime + delta
            run.endtime = run.endtime + delta
            run.save(fix_time=False, fix_runners=False)

        return callback

    results = {
        'changes': [
            (
                run,
                [
                    ('starttime', (run.starttime, run.starttime + delta)),
                    ('endtime', (run.endtime, run.endtime + delta)),
                ],
            )
            for run in runs
        ],
        'callbacks': [make_callback(run) for run in runs],
    }
    return results


@receiver(model_changed, sender=SpeedRun)
def adjust_order_after_null(sender, instance, **kwargs):
    old, new = instance
    if old.order is None or new.order is not None:
        return {}
    delta = old.total_length
    runs = SpeedRun.objects.filter(event=old.event, order__gt=old.order)
    if not runs:
        return {}
    results = {}

    def make_callback(run):
        def callback():
            run.starttime = run.starttime - delta
            run.endtime = run.endtime - delta
            run.save(fix_time=False, fix_runners=False)

        return callback

    for new_order, run in zip(range(old.order, old.order + len(runs)), runs):
        changes = [('order', (run.order, new_order))]
        run.order = new_order
        if run.starttime:
            changes.append(('starttime', (run.starttime, run.starttime - delta)))
            changes.append(('endtime', (run.endtime, run.endtime - delta)))
            results.setdefault('callbacks', []).append(make_callback(run))
        results.setdefault('changes', []).append((run, changes))
    return results


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
def runners_changed(sender, instance, action, **kwargs):
    if action[:4] == 'post':
        instance.save(fix_time=False, fix_runners=True)


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
