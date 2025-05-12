from collections import defaultdict

from django.core.exceptions import ValidationError
from django.db import models

from tracker import validators

from .fields import TimestampField


class InterstitialQuerySet(models.QuerySet):
    pass


class Interstitial(models.Model):
    class Manager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().prefetch_related('tags')

    objects = Manager.from_queryset(InterstitialQuerySet)()
    event = models.ForeignKey('tracker.event', on_delete=models.PROTECT)
    anchor = models.ForeignKey(
        'tracker.speedrun', on_delete=models.PROTECT, null=True, blank=True
    )
    # needs to be nullable to support moves when anchored, but should always fix itself coming out the other end
    order = models.IntegerField(
        validators=[validators.positive, validators.nonzero], null=True
    )
    suborder = models.IntegerField(validators=[validators.positive, validators.nonzero])
    length = TimestampField(always_show_m=True)
    tags = models.ManyToManyField(
        'tracker.Tag', related_name='interstitials', blank=True
    )

    class Meta:
        unique_together = ('event', 'order', 'suborder')
        ordering = ('event', 'order', 'suborder')

    @property
    def run(self):
        from .event import SpeedRun

        if self.anchor:
            return self.anchor
        if self.order is None:  # should never happen, but blows things up if it does
            return None
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
        if self.anchor_id and self.anchor.order is None:
            raise ValidationError({'anchor': 'anchored order cannot be blank'})
        if self.order is None and self.anchor is None:
            raise ValidationError(
                {'order': 'order cannot be null if the interstitial is not anchored'}
            )

    def __str__(self):
        return f'Interstitial({self.event_id},{self.anchor_id},{self.order},{self.suborder})'


class InterviewQuerySet(InterstitialQuerySet):
    def public(self, include_draft=False):
        qs = self
        if not include_draft:
            qs = self.filter(event__draft=False)
        return qs.filter(public=True)


class Interview(Interstitial):
    class Manager(Interstitial.Manager):
        def get_queryset(self):
            return super().get_queryset().prefetch_related('interviewers', 'subjects')

    objects = Manager.from_queryset(InterviewQuerySet)()
    interviewers = models.ManyToManyField(
        'tracker.Talent', related_name='interviewer_for'
    )
    subjects = models.ManyToManyField(
        'tracker.Talent',
        blank=True,
        help_text='i.e. interviewees',
        related_name='subject_for',
    )
    topic = models.CharField(max_length=128, help_text='what the interview is about')
    producer = models.CharField(max_length=128, blank=True)
    camera_operator = models.CharField(max_length=128, blank=True)
    social_media = models.BooleanField(default=False)
    clips = models.BooleanField(default=False)
    public = models.BooleanField(default=True)
    prerecorded = models.BooleanField(default=False)

    @property
    def interviewers_text(self):
        return ', '.join(i.name for i in self.interviewers.all())

    @property
    def subjects_text(self):
        return ', '.join(s.name for s in self.subjects.all())

    def __str__(self):
        if self.pk is None:
            return self.topic
        interviewers = self.interviewers_text
        subjects = self.subjects_text
        pieces = (
            (interviewers, subjects, self.topic)
            if subjects
            else (interviewers, self.topic)
        )
        return ' - '.join(pieces)


class AdQuerySet(InterstitialQuerySet):
    pass


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

    def __str__(self):
        return '%s - %s - %s' % (self.sponsor_name, self.ad_name, self.ad_type)
