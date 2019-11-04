from decimal import Decimal

from django.db import models
from django.db.models import signals
from django.db.models import Count, Sum, Max, Avg
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone

from .event import LatestEvent
from .fields import OneToOneOrNoneField
from ..validators import *
from functools import reduce

import calendar

__all__ = [
    "Donation",
    "Donor",
    "DonorCache",
]

_currencyChoices = (("USD", "US Dollars"), ("CAD", "Canadian Dollars"))

DonorVisibilityChoices = (
    ("FULL", "Fully Visible"),
    ("FIRST", "First Name, Last Initial"),
    ("ALIAS", "Alias Only"),
    ("ANON", "Anonymous"),
)

DonationDomainChoices = (("LOCAL", "Local"), ("CHIPIN", "ChipIn"), ("PAYPAL", "PayPal"))

LanguageChoices = (
    ("un", "Unknown"),
    ("en", "English"),
    ("fr", "French"),
    ("de", "German"),
)


class DonationManager(models.Manager):
    def get_by_natural_key(self, domainId):
        return self.get(domainId=domainId)


class Donation(models.Model):
    objects = DonationManager()
    donor = models.ForeignKey("Donor", on_delete=models.PROTECT, blank=True, null=True)
    event = models.ForeignKey("Event", on_delete=models.PROTECT, default=LatestEvent)
    domain = models.CharField(
        max_length=255, default="LOCAL", choices=DonationDomainChoices
    )
    domainId = models.CharField(max_length=160, unique=True, editable=False, blank=True)
    transactionstate = models.CharField(
        "Transaction State",
        max_length=64,
        db_index=True,
        default="PENDING",
        choices=(
            ("PENDING", "Pending"),
            ("COMPLETED", "Completed"),
            ("CANCELLED", "Cancelled"),
            ("FLAGGED", "Flagged"),
        ),
    )
    bidstate = models.CharField(
        "Bid State",
        max_length=255,
        db_index=True,
        default="PENDING",
        choices=(
            ("PENDING", "Pending"),
            ("IGNORED", "Ignored"),
            ("PROCESSED", "Processed"),
            ("FLAGGED", "Flagged"),
        ),
    )
    readstate = models.CharField(
        "Read State",
        max_length=255,
        db_index=True,
        default="PENDING",
        choices=(
            ("PENDING", "Pending"),
            ("READY", "Ready to Read"),
            ("IGNORED", "Ignored"),
            ("READ", "Read"),
            ("FLAGGED", "Flagged"),
        ),
    )
    commentstate = models.CharField(
        "Comment State",
        max_length=255,
        db_index=True,
        default="ABSENT",
        choices=(
            ("ABSENT", "Absent"),
            ("PENDING", "Pending"),
            ("DENIED", "Denied"),
            ("APPROVED", "Approved"),
            ("FLAGGED", "Flagged"),
        ),
    )
    amount = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        default=Decimal("0.00"),
        validators=[positive, nonzero],
        verbose_name="Donation Amount",
    )
    fee = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        default=Decimal("0.00"),
        validators=[positive],
        verbose_name="Donation Fee",
    )
    currency = models.CharField(
        max_length=8,
        null=False,
        blank=False,
        choices=_currencyChoices,
        verbose_name="Currency",
    )
    timereceived = models.DateTimeField(
        default=timezone.now, db_index=True, verbose_name="Time Received"
    )
    comment = models.TextField(blank=True, verbose_name="Comment")
    modcomment = models.TextField(blank=True, verbose_name="Moderator Comment")
    # Specifies if this donation is a 'test' donation, i.e. generated by a sandbox test, and should not be counted
    testdonation = models.BooleanField(default=False)
    requestedvisibility = models.CharField(
        max_length=32,
        null=False,
        blank=False,
        default="CURR",
        choices=(("CURR", "Use Existing (Anonymous if not set)"),)
        + DonorVisibilityChoices,
        verbose_name="Requested Visibility",
    )
    requestedalias = models.CharField(
        max_length=32, null=True, blank=True, verbose_name="Requested Alias"
    )
    requestedemail = models.EmailField(
        max_length=128, null=True, blank=True, verbose_name="Requested Contact Email"
    )
    requestedsolicitemail = models.CharField(
        max_length=32,
        null=False,
        blank=False,
        default="CURR",
        choices=(
            ("CURR", "Use Existing (Opt Out if not set)"),
            ("OPTOUT", "Opt Out"),
            ("OPTIN", "Opt In"),
        ),
        verbose_name="Requested Charity Email Opt In",
    )
    commentlanguage = models.CharField(
        max_length=32,
        null=False,
        blank=False,
        default="un",
        choices=LanguageChoices,
        verbose_name="Comment Language",
    )

    class Meta:
        app_label = "tracker"
        permissions = (
            ("delete_all_donations", "Can delete non-local donations"),
            ("view_full_list", "Can view full donation list"),
            ("view_comments", "Can view all comments"),
            ("view_pending", "Can view pending donations"),
            ("view_test", "Can view test donations"),
            ("send_to_reader", "Can send donations to the reader"),
        )
        get_latest_by = "timereceived"
        ordering = ["-timereceived"]

    def bid_total(self):
        return reduce(
            lambda a, b: a + b, [b.amount for b in self.bids.all()], Decimal("0.00")
        )

    def prize_ticket_amount(self, targetPrize):
        return sum([ticket.amount for ticket in self.tickets.filter(prize=targetPrize)])

    def anonymous(self):
        """Return whether the donation is anonymous or will be anonymous.

        This is an imperfect estimation, since donors can change their
        visibility at any time, including while a donation is processing.
        """
        if self.requestedvisibility == "ANON":
            return True

        if self.requestedvisibility == "CURR" and (
            self.donor and self.donor.visibility == "ANON"
        ):
            return True

        return False

    def clean(self, bid=None):
        super(Donation, self).clean()
        if self.domain == "LOCAL":  # local donations are always complete, duh
            if not self.donor:
                raise ValidationError("Local donations must have a donor")
            self.transactionstate = "COMPLETED"
        if not self.donor and self.transactionstate != "PENDING":
            raise ValidationError(
                "Donation must have a donor when in a non-pending state"
            )
        if not self.domainId and self.donor and self.timereceived:
            self.domainId = (
                str(calendar.timegm(self.timereceived.timetuple())) + self.donor.email
            )

        bids = set(self.bids.all())

        # because non-saved bids will not have an id, they are not hashable, so we have to special case them
        if bid:
            if not bid.id:
                bids = list(bids) + [bid]
            else:
                # N.B. the order here is very important, as we want the new copy of bid to override the old one (if present)
                bids = list({bid} | bids)

        bids = [b.amount or 0 for b in bids]
        bidtotal = reduce(lambda a, b: a + b, bids, Decimal("0"))
        if self.amount and bidtotal > self.amount:
            raise ValidationError(
                "Bid total is greater than donation amount: %s > %s"
                % (bidtotal, self.amount)
            )

        tickets = self.tickets.all()
        ticketTotal = reduce(
            lambda a, b: a + b, [b.amount for b in tickets], Decimal("0")
        )
        if self.amount and ticketTotal > self.amount:
            raise ValidationError(
                "Prize ticket total is greater than donation amount: %s > %s"
                % (ticketTotal, self.amount)
            )

        # TODO: language detection again?
        self.commentlanguage = "un"

    def approve_if_anonymous_and_no_comment(self, threshold=None):
        """
        If a donation is anonymous and has no comment, approve it.

        Above the threshold, send it to the reader. Below the threshold, just
        ignore it.

        If no threshold is provided, eligible donations are just ignored.
        """
        if self.anonymous_and_no_comment() and self.readstate == "PENDING":
            # With no threshold, ignore everything
            if not threshold:
                self.readstate = "IGNORED"
                return

            # With a threshold, do the right thing
            if self.amount >= threshold:
                self.readstate = "READY"
            else:
                self.readstate = "IGNORED"

    def anonymous_and_no_comment(self):
        return self.anonymous() and not self.comment

    def __str__(self):
        return (
            str(self.donor.visible_name() if self.donor else self.donor)
            + " ("
            + str(self.amount)
            + ") ("
            + str(self.timereceived)
            + ")"
        )


@receiver(signals.post_save, sender=Donation)
def DonationBidsUpdate(sender, instance, created, raw, **kwargs):
    if raw:
        return
    if instance.transactionstate == "COMPLETED":
        for b in instance.bids.all():
            b.save()


class DonorManager(models.Manager):
    def get_by_natural_key(self, email):
        return self.get(email=email)


class Donor(models.Model):
    objects = DonorManager()
    email = models.EmailField(max_length=128, verbose_name="Contact Email")
    alias = models.CharField(max_length=32, null=True, blank=True)
    firstname = models.CharField(max_length=64, blank=True, verbose_name="First Name")
    lastname = models.CharField(max_length=64, blank=True, verbose_name="Last Name")
    visibility = models.CharField(
        max_length=32,
        null=False,
        blank=False,
        default="FIRST",
        choices=DonorVisibilityChoices,
    )
    user = OneToOneOrNoneField(User, null=True, blank=True)

    # Address information, yay!
    addresscity = models.CharField(
        max_length=128, blank=True, null=False, verbose_name="City"
    )
    addressstreet = models.CharField(
        max_length=128, blank=True, null=False, verbose_name="Street/P.O. Box"
    )
    addressstate = models.CharField(
        max_length=128, blank=True, null=False, verbose_name="State/Province"
    )
    addresszip = models.CharField(
        max_length=128, blank=True, null=False, verbose_name="Zip/Postal Code"
    )
    addresscountry = models.ForeignKey(
        "Country", null=True, blank=True, default=None, verbose_name="Country"
    )

    # Donor specific info
    paypalemail = models.EmailField(
        max_length=128, unique=True, null=True, blank=True, verbose_name="Paypal Email"
    )
    solicitemail = models.CharField(
        max_length=32,
        choices=(
            ("CURR", "Use Existing (Opt Out if not set)"),
            ("OPTOUT", "Opt Out"),
            ("OPTIN", "Opt In"),
        ),
        default="CURR",
    )

    class Meta:
        app_label = "tracker"
        permissions = (
            ("delete_all_donors", "Can delete donors with cleared donations"),
            ("view_usernames", "Can view full usernames"),
            ("view_emails", "Can view email addresses"),
        )
        ordering = ["lastname", "firstname", "email"]

    def clean(self):
        # an empty value means a null value
        if not self.alias:
            self.alias = None
        if self.visibility == "ALIAS" and not self.alias:
            raise ValidationError(
                "Cannot set Donor visibility to 'Alias Only' without an alias"
            )
        if not self.paypalemail:
            self.paypalemail = None

    def contact_name(self):
        if self.firstname:
            return self.firstname + " " + self.lastname
        if self.alias:
            return self.alias
        return self.email

    ANONYMOUS = "(Anonymous)"

    def visible_name(self):
        if self.visibility == "ANON":
            return Donor.ANONYMOUS
        elif self.visibility == "ALIAS":
            return self.alias or "(No Name)"
        last_name, first_name = self.lastname, self.firstname
        if not last_name and not first_name:
            return self.alias or "(No Name)"
        if self.visibility == "FIRST":
            last_name = last_name[:1] + "..."
        return (
            last_name
            + ", "
            + first_name
            + ("" if self.alias == None else " (" + self.alias + ")")
        )

    def full(self):
        return str(self.email) + " (" + str(self) + ")"

    def get_absolute_url(self, event=None):
        return reverse(
            "tracker:donor",
            args=(self.id, event.id) if event and event.id else (self.id,),
        )

    def __repr__(self):
        return self.visible_name()

    def __str__(self):
        if not self.lastname and not self.firstname:
            return self.alias or "(No Name)"
        ret = str(self.lastname) + ", " + str(self.firstname)
        if self.alias:
            ret += " (" + str(self.alias) + ")"
        return ret


class DonorCache(models.Model):
    # null event = all events
    event = models.ForeignKey("Event", blank=True, null=True)
    donor = models.ForeignKey("Donor")
    donation_total = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        validators=[positive, nonzero],
        editable=False,
        default=0,
    )
    donation_count = models.IntegerField(
        validators=[positive, nonzero], editable=False, default=0
    )
    donation_avg = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        validators=[positive, nonzero],
        editable=False,
        default=0,
    )
    donation_max = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        validators=[positive, nonzero],
        editable=False,
        default=0,
    )

    @staticmethod
    @receiver(signals.post_save, sender=Donation)
    @receiver(signals.post_delete, sender=Donation)
    def donation_update(sender, instance, **args):
        if not instance.donor:
            return
        cache, c = DonorCache.objects.get_or_create(
            event=instance.event, donor=instance.donor
        )
        cache.update()
        if cache.donation_count:
            cache.save()
        else:
            cache.delete()
        cache, c = DonorCache.objects.get_or_create(event=None, donor=instance.donor)
        cache.update()
        if cache.donation_count:
            cache.save()
        else:
            cache.delete()

    def update(self):
        aggregate = Donation.objects.filter(
            donor=self.donor, transactionstate="COMPLETED"
        )
        if self.event:
            aggregate = aggregate.filter(event=self.event)
        aggregate = aggregate.aggregate(
            total=Sum("amount"),
            count=Count("amount"),
            max=Max("amount"),
            avg=Avg("amount"),
        )
        self.donation_total = aggregate["total"] or 0
        self.donation_count = aggregate["count"] or 0
        self.donation_max = aggregate["max"] or 0
        self.donation_avg = aggregate["avg"] or 0

    def __str__(self):
        return str(self.donor)

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
    def visible_name(self):
        return self.donor.visible_name

    @property
    def visibility(self):
        return self.donor.visibility

    def get_absolute_url(self, event=None):
        return self.donor.get_absolute_url(event)

    class Meta:
        app_label = "tracker"
        ordering = ("donor",)
        unique_together = ("event", "donor")
