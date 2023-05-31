from collections import defaultdict

from django.core.exceptions import ValidationError
from django.db import models

from tracker import validators

from .event import SpeedRun, TimestampField


class Interstitial(models.Model):
    event = models.ForeignKey('tracker.event', on_delete=models.PROTECT)
    order = models.IntegerField(validators=[validators.positive, validators.nonzero])
    suborder = models.IntegerField(validators=[validators.positive, validators.nonzero])
    length = TimestampField(always_show_m=True)

    class Meta:
        unique_together = ('event', 'order', 'suborder')
        ordering = ('event', 'order', 'suborder')

    @property
    def run(self):
        runs = SpeedRun.objects.filter(event=self.event)
        return (
            runs.filter(order__lte=self.order).last()
            or runs.filter(order__gte=self.order).first()
        )

    @staticmethod
    def interstitials_for_run(run):
        prev_run = SpeedRun.objects.filter(event=run.event, order__lt=run.order).last()
        next_run = SpeedRun.objects.filter(event=run.event, order__gt=run.order).first()
        interstitials = Interstitial.objects.filter(event=run.event)
        if prev_run:
            interstitials = interstitials.filter(order__gte=run.order)
        if next_run:
            interstitials = interstitials.filter(order__lt=next_run.order)
        return interstitials

    def validate_unique(self, exclude=None):
        errors = defaultdict(list)

        if exclude is None or 'suborder' not in exclude:
            existing = (
                Interstitial.objects.filter(
                    event=self.event, order=self.order, suborder=self.suborder
                )
                .exclude(id=self.id)
                .first()
            )
            if existing and existing != self:
                errors['suborder'].append(
                    'Interstitial already exists in this suborder slot'
                )
        try:
            super().validate_unique(exclude)
        except ValidationError as error:
            error.update_error_dict(errors)
        if errors:
            raise ValidationError(errors)


class Interview(Interstitial):
    interviewers = models.CharField(max_length=128)
    subjects = models.CharField(max_length=128)
    topic = models.CharField(max_length=128)
    producer = models.CharField(max_length=128, blank=True)
    camera_operator = models.CharField(max_length=128, blank=True)
    social_media = models.BooleanField()
    clips = models.BooleanField()

    class Meta:
        permissions = (('view_interviews', 'Can view interviews'),)

    def __str__(self):
        return '%s - %s - %s' % (self.interviewers, self.subjects, self.topic)


class Ad(Interstitial):
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
