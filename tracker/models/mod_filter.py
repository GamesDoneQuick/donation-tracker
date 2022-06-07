import re

from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from tracker.analytics import analytics, AnalyticsEventTypes
from .donation import Donation

__all__ = [
    'WordFilter',
    'AmountFilter',
]


class WordFilter(models.Model):
    word = models.CharField(max_length=32)

    def __str__(self):
        return f'WordFilter: {self.word}'


class AmountFilter(models.Model):
    amount = models.DecimalField(max_digits=20, decimal_places=2)

    def __str__(self):
        return f'AmountFilter: {self.amount}'


@receiver(pre_save, sender=Donation)
def moderation_filter(sender, instance, raw, using, update_fields, **kwargs):
    if instance.id:
        return
    words = WordFilter.objects.using(using).all()
    for word in words:
        if re.search(r'\b%s\b' % word.word.lower(), instance.comment.lower()):
            instance.modcomment += (
                '\nDENIED due to matching filter word: %s' % word.word.lower()
            )
            instance.commentstate = 'DENIED'
            instance.readstate = 'IGNORED'
            analytics.track(
                AnalyticsEventTypes.DONATION_COMMENT_AUTOMOD_DENIED,
                {
                    'donation_id': instance.id,
                    'event_id': instance.event_id,
                    'filter_kind': 'word',
                    'filter_value': word.word.lower(),
                    'donation_value': instance.comment,
                },
            )

    amounts = AmountFilter.objects.using(using).all()
    for amount in amounts:
        if amount.amount == instance.amount:
            instance.modcomment += (
                '\nDENIED due to matching filter amount: %s' % amount.amount
            )
            instance.commentstate = 'DENIED'
            instance.readstate = 'IGNORED'
            analytics.track(
                AnalyticsEventTypes.DONATION_COMMENT_AUTOMOD_DENIED,
                {
                    'donation_id': instance.id,
                    'event_id': instance.event_id,
                    'filter_kind': 'amount',
                    'filter_value': str(amount.amount),
                    'donation_value': str(instance.amount),
                },
            )
