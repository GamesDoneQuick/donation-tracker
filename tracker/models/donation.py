import datetime
import logging
import random
import time
from collections import defaultdict
from decimal import Decimal
from functools import reduce

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.signing import Signer
from django.db import models
from django.db.models import (
    Avg,
    Count,
    FloatField,
    Index,
    Max,
    Prefetch,
    Q,
    Sum,
    signals,
)
from django.db.models.functions import Cast, Coalesce
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone

from .. import settings, util
from ..util import median
from ..validators import nonzero, positive
from .fields import OneToOneOrNoneField
from .tag import AbstractTag
from .util import LatestEvent

__all__ = [
    'Donation',
    'DonationGroup',
    'Donor',
    'DonorCache',
    'Milestone',
]

_currencyChoices = (
    ('USD', 'US Dollars'),
    ('CAD', 'Canadian Dollars'),
    ('EUR', 'Euros'),
)

DonorVisibilityChoices = (
    ('FULL', 'Fully Visible'),
    ('FIRST', 'First Name, Last Initial'),
    ('ALIAS', 'Alias Only'),
    ('ANON', 'Anonymous'),
)

DonationDomainChoices = (('LOCAL', 'Local'), ('CHIPIN', 'ChipIn'), ('PAYPAL', 'PayPal'))

LanguageChoices = (
    ('un', 'Unknown'),
    ('en', 'English'),
    ('fr', 'French'),
    ('de', 'German'),
)

logger = logging.getLogger(__name__)


class DonationQuerySet(models.QuerySet):
    def completed(self):
        qs = self
        if not settings.PAYPAL_TEST:
            qs = qs.filter(testdonation=False)
        return qs.filter(transactionstate='COMPLETED')

    def pending(self):
        return self.filter(transactionstate='PENDING')

    def cancelled(self):
        return self.filter(transactionstate='CANCELLED')

    def flagged(self):
        return self.filter(transactionstate='FLAGGED')

    def recent(self, offset: int, now=None):
        if now is None:
            now = util.utcnow()
        return self.completed().filter(
            timereceived__gte=now - datetime.timedelta(minutes=offset)
        )

    def to_process(self):
        return self.completed().filter(
            Q(commentstate='PENDING') | Q(readstate='PENDING')
        )

    def to_approve(self):
        return self.completed().filter(readstate='FLAGGED')

    def to_read(self):
        return self.completed().filter(readstate='READY')

    def prefetch_public_bids(self):
        from tracker.models import Bid, DonationBid

        bids = Bid.objects.public()

        return self.prefetch_related(
            Prefetch('bids', queryset=DonationBid.objects.public()),
            Prefetch('bids__bid', queryset=bids),
            'bids__bid__speedrun',
            'bids__bid__event',
        )


class DonationGroup(AbstractTag):
    pass


class DonationManager(models.Manager):
    def get_by_natural_key(self, domainId):
        return self.get(domainId=domainId)


class Donation(models.Model):
    objects = DonationManager.from_queryset(DonationQuerySet)()
    donor = models.ForeignKey('Donor', on_delete=models.PROTECT, blank=True, null=True)
    event = models.ForeignKey('Event', on_delete=models.PROTECT, default=LatestEvent)
    domain = models.CharField(
        max_length=255, default='LOCAL', choices=DonationDomainChoices
    )
    groups = models.ManyToManyField('tracker.DonationGroup', blank=True)
    domainId = models.CharField(max_length=160, unique=True, editable=False, blank=True)
    transactionstate = models.CharField(
        'Transaction State',
        max_length=64,
        db_index=True,
        default='PENDING',
        choices=(
            ('PENDING', 'Pending'),
            ('COMPLETED', 'Completed'),
            ('CANCELLED', 'Cancelled'),
            ('FLAGGED', 'Flagged'),
        ),
    )
    bidstate = models.CharField(
        'Bid State',
        max_length=255,
        db_index=True,
        default='PENDING',
        choices=(
            ('PENDING', 'Pending'),
            ('IGNORED', 'Ignored'),
            ('PROCESSED', 'Processed'),
            ('FLAGGED', 'Flagged'),
        ),
    )
    readstate = models.CharField(
        'Read State',
        max_length=255,
        db_index=True,
        default='PENDING',
        choices=(
            ('PENDING', 'Pending'),
            ('READY', 'Ready to Read'),
            ('IGNORED', 'Ignored'),
            ('READ', 'Read'),
            ('FLAGGED', 'Flagged'),  # two pass
        ),
    )
    commentstate = models.CharField(
        'Comment State',
        max_length=255,
        db_index=True,
        default='ABSENT',
        choices=(
            ('ABSENT', 'Absent'),
            ('PENDING', 'Pending'),
            ('DENIED', 'Denied'),
            ('APPROVED', 'Approved'),
            ('FLAGGED', 'Flagged'),
        ),
    )
    amount = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        db_index=True,
        default=Decimal('0.00'),
        validators=[positive, nonzero],
        verbose_name='Donation Amount',
    )
    fee = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        default=Decimal('0.00'),
        validators=[positive],
        verbose_name='Donation Fee',
    )
    currency = models.CharField(
        max_length=8,
        null=False,
        blank=False,
        choices=_currencyChoices,
        verbose_name='Currency',
    )
    timereceived = models.DateTimeField(
        default=timezone.now, db_index=True, verbose_name='Time Received'
    )
    comment = models.TextField(blank=True, verbose_name='Comment')
    modcomment = models.TextField(blank=True, verbose_name='Moderator Comment')
    # Specifies if this donation is a 'test' donation, i.e. generated by a sandbox test, and should not be counted
    testdonation = models.BooleanField(default=False)
    requestedvisibility = models.CharField(
        max_length=32,
        null=False,
        blank=False,
        default='CURR',
        choices=(('CURR', 'Use Existing (Anonymous if not set)'),)
        + DonorVisibilityChoices,
        verbose_name='Requested Visibility',
    )
    requestedalias = models.CharField(
        max_length=32, default='', blank=True, verbose_name='Requested Alias'
    )
    requestedemail = models.EmailField(
        max_length=128, default='', blank=True, verbose_name='Requested Contact Email'
    )
    requestedsolicitemail = models.CharField(
        max_length=32,
        null=False,
        blank=False,
        default='CURR',
        choices=(
            ('CURR', 'Use Existing (Opt Out if not set)'),
            ('OPTOUT', 'Opt Out'),
            ('OPTIN', 'Opt In'),
        ),
        verbose_name='Requested Charity Email Opt In',
    )
    commentlanguage = models.CharField(
        max_length=32,
        null=False,
        blank=False,
        default='un',
        choices=LanguageChoices,
        verbose_name='Comment Language',
    )
    pinned = models.BooleanField(default=False)
    # domainId is unique but this is the best way to get this relation without monkeypatching
    ipns = models.ManyToManyField('ipn.paypalipn', blank=True, related_name='donation')
    cleared_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        app_label = 'tracker'
        permissions = (
            ('delete_all_donations', 'Can delete non-local donations'),
            ('view_comments', 'Can view all comments'),
            ('view_pending_donation', 'Can view pending donations'),
            ('view_test', 'Can view test donations'),
            ('send_to_reader', 'Can send donations to the reader'),
        )
        get_latest_by = 'timereceived'
        ordering = ['-timereceived']
        indexes = (
            *(
                Index(
                    column,
                    name=f'{column}_completed',
                    condition=Q(testdonation=False, transactionstate='COMPLETED'),
                )
                for column in ('amount',)
            ),
            *(
                Index(
                    column,
                    'event_id',
                    name=f'{column}_event_completed',
                    condition=Q(testdonation=False, transactionstate='COMPLETED'),
                )
                for column in (
                    'donor_id',
                    'amount',
                    'commentstate',
                    'readstate',
                    'timereceived',
                )
            ),
        )

    def user_can_send_to_reader(self, user):
        """returns True if
        a) the event is set
         AND
        b.1) the event is not using two pass mode
         OR
        b.2) the user has `send_to_reader` permission"""
        return self.event and (
            self.event.screening_mode != 'two_pass'
            or user.has_perm('tracker.send_to_reader')
        )

    @property
    def visible_donor_name(self):
        if self.requestedvisibility == 'ANON':
            return Donor.ANONYMOUS
        # TODO: allow Donors to edit the visibility in certain limited ways (needs discussion)
        return self.requestedalias

    @property
    def donor_cache(self):
        return self.donor.cache_for(self.event_id)

    def get_paypal_signature(self):
        """id is used twice to make it easier to scan IPNs that correspond to a given donation, and then to verify
        the signature"""
        signer = Signer(salt=str(Decimal(self.amount).quantize(Decimal('0.00'))))
        prefix = settings.TRACKER_PAYPAL_SIGNATURE_PREFIX
        assert (
            isinstance(prefix, str) and 1 <= len(prefix) <= 8
        ), 'TRACKER_PAYPAL_SIGNATURE_PREFIX incorrectly configured'
        signature = signer.sign_object(
            {'id': self.id, 'domainId': self.domainId}, compress=True
        )
        return f'{prefix}:{self.id}:{signature}'

    get_paypal_signature.short_description = 'PayPal Signature'

    paypal_signature = property(get_paypal_signature)

    def get_absolute_url(self):
        return util.build_public_url(reverse('tracker:donation', args=(self.id,)))

    def bid_total(self):
        return reduce(
            lambda a, b: a + b, [b.amount for b in self.bids.all()], Decimal('0.00')
        )

    def anonymous(self):
        """Return whether the donation is anonymous or will be anonymous.

        This is an imperfect estimation, since donors can change their
        visibility at any time, including while a donation is processing.
        """
        if self.requestedvisibility == 'ANON':
            return True

        if self.requestedvisibility == 'CURR' and (
            self.donor and self.donor.visibility == 'ANON'
        ):
            return True

        return False

    def clean(self):
        super(Donation, self).clean()
        errors = defaultdict(list)
        if self.domain == 'LOCAL' and not self.donor:
            errors['donor'].append('Local donations must have a donor')
        if self.transactionstate != 'PENDING' and not self.donor:
            errors['donor'].append(
                'Donation must have a donor when in a non-pending state'
            )

        if self.id:
            bids = set(self.bids.all())
        else:
            bids = []

        bidtotal = reduce(lambda a, b: a + b, (b.amount for b in bids), Decimal(0))
        if self.amount and bidtotal > self.amount:
            errors['amount'].append(
                'Bid total is greater than donation amount: %s > %s'
                % (bidtotal, self.amount)
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.readstate == 'PENDING':
            if self.event.screening_mode == 'host_only':
                self.readstate = 'READY'
            elif (
                (threshold := self.event.auto_approve_threshold) is not None
                and self.anonymous()
                and not self.comment
            ):
                # when a threshold is set, anonymous, no-comment donations are
                # either sent right to the reader or ignored
                if self.amount >= threshold:
                    self.readstate = 'READY'
                else:
                    self.readstate = 'IGNORED'
        elif self.readstate == 'FLAGGED' and self.event.screening_mode != 'two_pass':
            # this is one side of an edge case involving this flag, see the event model for the other
            self.readstate = 'READY'
        if not self.timereceived:
            self.timereceived = util.utcnow()
        if self.domain == 'LOCAL':  # local donations are always complete, duh
            self.cleared_at = self.timereceived
            self.transactionstate = 'COMPLETED'
        # reminder that this does not run during migrations tests, so you have to provide the domainId yourself
        if not self.domainId:
            self.domainId = f'{int(time.time())}-{random.getrandbits(128)}'
        self.requestedalias = self.requestedalias.strip()
        self.requestedemail = self.requestedemail.strip()
        self.comment = self.comment.strip()
        if self.comment == '':
            self.commentstate = 'ABSENT'
        elif self.commentstate == 'ABSENT':
            self.commentstate = 'PENDING'
        # TODO: language detection again?
        self.commentlanguage = 'un'

        post = self.id is None and self.domain == 'LOCAL'

        super(Donation, self).save(*args, **kwargs)

        if post:
            from .. import settings, tasks

            if settings.TRACKER_HAS_CELERY:
                tasks.post_donation_to_postbacks.delay(self.id)
            else:
                tasks.post_donation_to_postbacks(self.id)

    def __str__(self):
        donor_name = self.donor.visible_name if self.donor else '(Unconfirmed)'
        return f'{donor_name} ({self.amount}) {self.timereceived}'


@receiver(signals.post_save, sender=Donation)
def donation_bids_update(sender, instance, created, raw, **kwargs):
    if raw:
        return
    if instance.transactionstate == 'COMPLETED':
        for b in instance.bids.all():
            b.save()


class DonorManager(models.Manager):
    def get_by_natural_key(self, email):
        return self.get(email=email)


class Donor(models.Model):
    objects = DonorManager()
    email = models.EmailField(max_length=128, verbose_name='Contact Email')
    alias = models.CharField(max_length=32, null=True, blank=True)
    alias_num = models.IntegerField(
        blank=True, editable=False, null=True, verbose_name='Alias Number'
    )
    firstname = models.CharField(max_length=64, blank=True, verbose_name='First Name')
    lastname = models.CharField(max_length=64, blank=True, verbose_name='Last Name')
    visibility = models.CharField(
        max_length=32,
        null=False,
        blank=False,
        default='FIRST',
        choices=DonorVisibilityChoices,
        db_index=True,
    )
    user = OneToOneOrNoneField(User, null=True, blank=True, on_delete=models.SET_NULL)

    addressname = models.CharField(
        max_length=128,
        blank=True,
        verbose_name='Shipping Name',
    )
    addresscity = models.CharField(max_length=128, blank=True, verbose_name='City')
    addressstreet = models.CharField(
        max_length=128, blank=True, verbose_name='Street/P.O. Box'
    )
    addressstate = models.CharField(
        max_length=128, blank=True, verbose_name='State/Province'
    )
    addresszip = models.CharField(
        max_length=128, blank=True, verbose_name='Zip/Postal Code'
    )
    addresscountry = models.ForeignKey(
        'Country',
        null=True,
        blank=True,
        default=None,
        verbose_name='Country',
        on_delete=models.PROTECT,
    )

    # Donor specific info
    paypalemail = models.EmailField(
        max_length=128, unique=True, null=True, blank=True, verbose_name='Paypal Email'
    )
    solicitemail = models.CharField(
        max_length=32,
        choices=(
            ('CURR', 'Use Existing (Opt Out if not set)'),
            ('OPTOUT', 'Opt Out'),
            ('OPTIN', 'Opt In'),
        ),
        default='CURR',
    )

    class Meta:
        app_label = 'tracker'
        permissions = (
            ('delete_all_donors', 'Can delete donors with cleared donations'),
            # the following two permissions are for the search fields only, and the names permission should not be
            #  considered a full privacy filter, as there are many places in the admin where the full name shows up if
            #  a user has other view permissions, regardless of Donor anonymity settings
            ('view_full_names', 'Can search for donors by full name'),
            ('view_emails', 'Can search for donors by email address'),
        )
        ordering = ['lastname', 'firstname', 'email']
        unique_together = [('alias', 'alias_num')]

    def save(self, *args, **kwargs):
        # an empty value means a null value
        if not self.alias:
            self.alias = None
            self.alias_num = None
        elif not self.alias_num:
            existing = set(d.alias_num for d in Donor.objects.filter(alias=self.alias))
            available = [i for i in range(1000, 10000) if i not in existing]
            if not available:
                logger.warning(
                    f'Could not set alias `{self.alias}` because the namespace was full'
                )
                self.alias = None
                self.alias_num = None
            else:
                self.alias_num = random.choice(available)
        if self.visibility == 'ALIAS' and not self.alias:
            self.visibility = 'ANON'
        if not self.paypalemail:
            self.paypalemail = None
        super(Donor, self).save(*args, **kwargs)

    def contact_name(self):
        if self.firstname:
            return self.firstname + ' ' + self.lastname
        if self.alias:
            return self.alias
        return self.email

    ANONYMOUS = '(Anonymous)'

    def cache_for(self, event_id=None):
        # avoid breaking prefetch
        return next((dc for dc in self.cache.all() if dc.event_id == event_id), None)

    @property
    def visible_name(self):
        # TODO: clean this up a bit
        if self.visibility == 'ANON':
            return Donor.ANONYMOUS
        elif self.visibility == 'ALIAS':
            if self.alias:
                return self.full_alias
            else:
                return Donor.ANONYMOUS
        last_name, first_name = self.lastname, self.firstname
        if not last_name and not first_name:
            return self.alias or '(No Name)'
        if self.visibility == 'FIRST':
            last_name = last_name[:1] + '...'
        alias = f' ({self.alias})' if self.alias else ''
        return f'{last_name}, {first_name}{alias}'

    @property
    def full_visible_name(self):
        # TODO: clean this up a bit
        if self.visibility == 'ANON':
            return Donor.ANONYMOUS
        elif self.visibility == 'ALIAS':
            return self.full_alias or Donor.ANONYMOUS
        last_name, first_name = self.lastname, self.firstname
        if not last_name and not first_name:
            return self.full_alias or '(No Name)'
        if self.visibility == 'FIRST':
            last_name = last_name[:1] + '...'
        alias = f' ({self.full_alias})' if self.alias else ''
        return f'{last_name}, {first_name}{alias}'

    @property
    def full_name(self):
        if self.firstname:
            if self.lastname:
                return f'{self.lastname}, {self.firstname}'
            else:
                return self.firstname
        else:
            return '(No Name Supplied)'

    @property
    def full_alias(self):
        if self.alias:
            return f'{self.alias}#{self.alias_num}'
        return None

    # disabled for now
    # def get_absolute_url(self):
    #     return reverse(
    #         'tracker:donor',
    #         args=(self.id,),
    #     )

    def __repr__(self):
        return self.visible_name

    def __str__(self):
        if not self.lastname and not self.firstname:
            return self.alias or '(No Name)'
        alias = f' ({self.alias})' if self.alias else ''
        return f'{self.lastname}, {self.firstname}{alias}'


class DonorCache(models.Model):
    # null event = all events
    event = models.ForeignKey('Event', blank=True, null=True, on_delete=models.CASCADE)
    # split by currency, only for "all events"
    currency = models.CharField(max_length=16, blank=True, null=True)
    # null donor = all donors
    donor = models.ForeignKey(
        'Donor', blank=True, null=True, on_delete=models.CASCADE, related_name='cache'
    )
    donation_total = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        editable=False,
        default=0,
        db_index=True,
    )
    donation_count = models.IntegerField(
        editable=False,
        default=0,
        db_index=True,
    )
    donation_avg = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        editable=False,
        default=0,
        db_index=True,
    )
    donation_max = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        editable=False,
        default=0,
        db_index=True,
    )
    donation_med = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        editable=False,
        default=0,
        db_index=True,
    )

    @staticmethod
    @receiver(signals.post_save, sender=Donation)
    @receiver(signals.post_delete, sender=Donation)
    def donation_update(sender, instance, **args):
        if not instance.donor:
            return

        DonorCache.objects.get_or_create(event=instance.event, donor=instance.donor)[
            0
        ].update()
        DonorCache.objects.get_or_create(
            event=None, donor=instance.donor, currency=instance.event.paypalcurrency
        )[0].update()
        DonorCache.objects.get_or_create(event=instance.event, donor=None)[0].update()
        DonorCache.objects.get_or_create(
            event=None, donor=None, currency=instance.event.paypalcurrency
        )[0].update()

    def update(self):
        # TODO: separate caches for test donations?
        donations = Donation.objects.completed().filter(testdonation=False)
        if self.donor:
            donations = donations.filter(donor=self.donor)
        if self.event:
            donations = donations.filter(event=self.event)
        else:
            donations = donations.filter(event__paypalcurrency=self.currency)
        aggregate = donations.aggregate(
            total=Cast(Coalesce(Sum('amount'), 0.0), output_field=FloatField()),
            count=Coalesce(Count('amount'), 0),
            max=Cast(Coalesce(Max('amount'), 0.0), output_field=FloatField()),
            avg=Cast(Coalesce(Avg('amount'), 0.0), output_field=FloatField()),
        )
        self.donation_total = aggregate['total']
        self.donation_count = aggregate['count']
        self.donation_max = aggregate['max']
        self.donation_avg = aggregate['avg']
        self.donation_med = median(donations, 'amount', count=aggregate['count'])
        if self.donation_count:
            self.save()
        else:
            self.delete()

    def __str__(self):
        parts = [self.donor or 'All Donors', self.event or 'All Events']
        if self.event is None:
            parts.append(self.currency)

        return ' -- '.join(str(p) for p in parts)

    @property
    def donation_set(self):
        return self.donor.donation_set

    @property
    def email(self):
        return self.donor.email

    @property
    def alias(self):
        return self.donor.alias

    @property
    def full_alias(self):
        return self.donor.full_alias

    @property
    def visible_name(self):
        return self.donor.visible_name

    @property
    def full_visible_name(self):
        return self.donor.full_visible_name

    @property
    def full_name(self):
        return self.donor.full_name

    @property
    def firstname(self):
        return self.donor.firstname

    @property
    def lastname(self):
        return self.donor.lastname

    @property
    def visibility(self):
        return self.donor.visibility

    @property
    def addresscountry(self):
        return self.donor.addresscountry

    # def get_absolute_url(self):
    #     args = (
    #         (
    #             self.donor_id,
    #             self.event_id,
    #         )
    #         if self.event_id
    #         else (self.donor_id,)
    #     )
    #     return reverse('tracker:donor', args=args)

    class Meta:
        app_label = 'tracker'
        ordering = ('donor',)
        unique_together = ('event', 'donor')
        verbose_name = 'Donor Total'


class MilestoneQuerySet(models.QuerySet):
    def public(self, include_draft=False):
        qs = self
        if not include_draft:
            qs = self.filter(event__draft=False)
        return qs.filter(visible=True)


class Milestone(models.Model):
    objects = models.Manager.from_queryset(MilestoneQuerySet)()
    event = models.ForeignKey('tracker.Event', on_delete=models.CASCADE)
    start = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        default=Decimal('0.00'),
        validators=[positive],
    )
    amount = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        default=Decimal('0.00'),
        validators=[positive, nonzero],
    )
    name = models.CharField(max_length=64)
    run = models.ForeignKey(
        'tracker.SpeedRun',
        blank=True,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
    )
    visible = models.BooleanField(default=False)
    description = models.TextField(max_length=1024, blank=True)
    short_description = models.TextField(
        max_length=256,
        blank=True,
        verbose_name='Short Description',
        help_text='Alternative description text to display in tight spaces',
    )

    def clean(self):
        if self.start >= self.amount:
            raise ValidationError({'start': 'start must be less than amount'})
        if self.run_id and self.run.event_id != self.event_id:
            raise ValidationError({'run': 'Run does not belong to that event'})

    def __str__(self):
        return f'{self.event.name} -- {self.name} -- {self.amount}'

    class Meta:
        app_label = 'tracker'
        ordering = ('event', 'amount')
        unique_together = ('event', 'amount')
