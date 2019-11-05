from django.db import models
from django.contrib.auth.models import User

from .event import (
    Event,
    PostbackURL,
    Runner,
    SpeedRun,
    Submission,
)
from .bid import Bid, BidSuggestion, DonationBid
from .donation import Donation, Donor, DonorCache
from .prize import (
    DonorPrizeEntry,
    Prize,
    PrizeCategory,
    PrizeKey,
    PrizeTicket,
    PrizeWinner,
)
from .country import Country, CountryRegion
from .mod_filter import AmountFilter, WordFilter

__all__ = [
    'Event',
    'PostbackURL',
    'Bid',
    'DonationBid',
    'BidSuggestion',
    'Donation',
    'Donor',
    'DonorCache',
    'Prize',
    'PrizeKey',
    'PrizeCategory',
    'PrizeTicket',
    'PrizeWinner',
    'DonorPrizeEntry',
    'SpeedRun',
    'Runner',
    'Submission',
    'UserProfile',
    'Log',
    'Country',
    'CountryRegion',
    'WordFilter',
    'AmountFilter',
]


class UserProfile(models.Model):
    user = models.OneToOneField(User)
    prepend = models.CharField('Template Prepend', max_length=64, blank=True)

    class Meta:
        verbose_name = 'User Profile'
        permissions = (
            ('show_rendertime', 'Can view page render times'),
            ('show_queries', 'Can view database queries'),
            ('can_search', 'Can use search url'),
        )

    def __str__(self):
        return str(self.user)


class Log(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Timestamp')
    category = models.CharField(
        max_length=64, default='other', blank=False, null=False, verbose_name='Category'
    )
    message = models.TextField(blank=True, null=False, verbose_name='Message')
    event = models.ForeignKey('Event', blank=True, null=True, on_delete=models.PROTECT)
    user = models.ForeignKey(User, blank=True, null=True)

    class Meta:
        verbose_name = 'Log'
        permissions = (
            ('can_view_log', 'Can view tracker logs'),
            ('can_change_log', 'Can change tracker logs'),
        )
        ordering = ['-timestamp']

    def __str__(self):
        result = str(self.timestamp)
        if self.event:
            result += ' (' + self.event.short + ')'
        result += ' -- ' + self.category
        if self.message:
            m = self.message
            if len(m) > 18:
                m = m[:15] + '...'
            result += ': ' + m
        return result
