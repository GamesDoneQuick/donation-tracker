from collections import defaultdict

from django.core.exceptions import ValidationError
from django.db import models

from tracker import validators

from .event import SpeedRun, TimestampField


class InterstitialQuerySet(models.QuerySet):
    def for_run(self, run):
        if run.order is None:
            return self.none()
        prev_run = SpeedRun.objects.filter(event=run.event, order__lt=run.order).last()
        next_run = SpeedRun.objects.filter(event=run.event, order__gt=run.order).first()
        interstitials = self.filter(event=run.event)
        if prev_run:
            interstitials = interstitials.filter(order__gte=run.order)
        if next_run:
            interstitials = interstitials.filter(order__lt=next_run.order)
        return interstitials


class Interstitial(models.Model):
    objects = models.Manager.from_queryset(InterstitialQuerySet)()
    event = models.ForeignKey('tracker.event', on_delete=models.PROTECT)
    anchor = models.ForeignKey(
        'tracker.speedrun', on_delete=models.PROTECT, null=True, blank=True
    )
    # needs to be nullable to support moves when anchored
    order = models.IntegerField(
        validators=[validators.positive, validators.nonzero], null=True
    )
    suborder = models.IntegerField(validators=[validators.positive, validators.nonzero])
    length = TimestampField(always_show_m=True)

    class Meta:
        unique_together = ('event', 'order', 'suborder')
        ordering = ('event', 'order', 'suborder')

    @property
    def run(self):
        if self.anchor:
            return self.anchor
        runs = SpeedRun.objects.filter(event=self.event)
        return (
            runs.filter(order__lte=self.order).last()
            or runs.filter(order__gte=self.order).first()
        )

    def validate_unique(self, exclude=None):
        errors = defaultdict(list)

        if exclude is None or 'suborder' not in exclude:
            if self.anchor:
                order = self.anchor.order
            else:
                order = self.order
            if (
                type(self)
                .objects.filter(event=self.event, order=order, suborder=self.suborder)
                .exclude(id=self.id)
                .exists()
            ):
                errors['suborder'].append(
                    'Interstitial already exists in this suborder slot'
                )

        try:
            super().validate_unique(exclude)
        except ValidationError as error:
            error.update_error_dict(errors)
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # FIXME: better way to force normalization?

        self.length = self._meta.get_field('length').to_python(self.length)
        if self.anchor:
            self.order = self.anchor.order

        super().save(*args, **kwargs)

    def clean(self):
        if self.order is None and self.run is None:
            raise ValidationError(
                {'order': 'order cannot be null if the interstitial is not anchored'}
            )


class InterviewQuerySet(InterstitialQuerySet):
    def for_run(self, run):
        interstitials = Interstitial.objects.for_run(run)
        return self.filter(interstitial_ptr__in=interstitials)

    def public(self):
        return self.filter(public=True)


class Interview(Interstitial):
    objects = models.Manager.from_queryset(InterviewQuerySet)()
    interviewers = models.CharField(max_length=128)
    subjects = models.CharField(
        max_length=128, blank=True, help_text='i.e. interviewees'
    )
    topic = models.CharField(max_length=128, help_text='what the interview is about')
    producer = models.CharField(max_length=128, blank=True)
    camera_operator = models.CharField(max_length=128, blank=True)
    social_media = models.BooleanField(default=False)
    clips = models.BooleanField(default=False)
    public = models.BooleanField(default=True)
    prerecorded = models.BooleanField(default=False)

    def __str__(self):
        pieces = (
            (self.interviewers, self.subjects, self.topic)
            if self.subjects
            else (self.interviewers, self.topic)
        )
        return ' - '.join(pieces)


class AdQuerySet(InterstitialQuerySet):
    def for_run(self, run):
        interstitials = Interstitial.objects.for_run(run)
        return self.filter(interstitial_ptr__in=interstitials)


class Ad(Interstitial):
    objects = models.Manager.from_queryset(AdQuerySet)()
    sponsor_name = models.CharField(max_length=64)
    ad_name = models.CharField(max_length=64)
    ad_type = models.CharField(
        max_length=8, choices=(('VIDEO', 'Video'), ('IMAGE', 'Image'))
    )
    filename = models.CharField(max_length=64)
    blurb = models.TextField(blank=True, help_text='Text for hosts to read off')

    class Meta:
        unique_together = ('sponsor_name', 'ad_name')
        permissions = (('view_ads', 'Can view ads'),)

    def __str__(self):
        return '%s - %s - %s' % (self.sponsor_name, self.ad_name, self.ad_type)
