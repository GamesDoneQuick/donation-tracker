from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from tracker import models
from .forms import (
    DonationBidForm,
    DonationForm,
    PrizeWinnerForm,
    DonorPrizeEntryForm,
    PrizeForm,
)


class CustomStackedInline(admin.StackedInline):
    # Adds an link that lets you edit an in-line linked object
    def edit_link(self, instance):
        if instance.id is not None:
            url = reverse(
                'admin:{label}_{merge}_change'.format(
                    label=instance._meta.app_label, merge=instance._meta.model_name
                ),
                args=[instance.id],
            )
            return mark_safe('<a href="{u}">Edit</a>'.format(u=url))
        else:
            return mark_safe('Not Saved Yet')


class DonationBidInline(CustomStackedInline):
    form = DonationBidForm
    model = models.DonationBid
    extra = 0
    max_num = 100
    readonly_fields = ('edit_link',)


class BidInline(CustomStackedInline):
    model = models.Bid
    fieldsets = [
        (
            None,
            {
                'fields': [
                    'name',
                    'description',
                    'shortdescription',
                    'istarget',
                    'goal',
                    'state',
                    'total',
                    'edit_link',
                ],
            },
        )
    ]
    extra = 0
    readonly_fields = (
        'total',
        'edit_link',
    )
    ordering = ('-total', 'name')


class BidOptionInline(BidInline):
    verbose_name_plural = 'Options'
    verbose_name = 'Option'
    fk_name = 'parent'


class BidDependentsInline(BidInline):
    verbose_name_plural = 'Dependent Bids'
    verbose_name = 'Dependent Bid'
    fk_name = 'biddependency'


class DonationInline(CustomStackedInline):
    form = DonationForm
    model = models.Donation
    extra = 0
    readonly_fields = ('edit_link',)


class EventBidInline(BidInline):
    def get_queryset(self, request):
        qs = super(EventBidInline, self).get_queryset(request)
        return qs.filter(speedrun=None)


class PrizeWinnerInline(CustomStackedInline):
    form = PrizeWinnerForm
    model = models.PrizeWinner
    readonly_fields = ['winner_email', 'edit_link']

    def winner_email(self, obj):
        return obj.winner.email

    extra = 0


class DonorPrizeEntryInline(CustomStackedInline):
    form = DonorPrizeEntryForm
    model = models.DonorPrizeEntry
    readonly_fields = ['edit_link']
    extra = 0


class PrizeInline(CustomStackedInline):
    model = models.Prize
    form = PrizeForm
    fk_name = 'endrun'
    extra = 0
    fields = [
        'name',
        'description',
        'shortdescription',
        'handler',
        'image',
        'altimage',
        'event',
        'state',
        'allowed_prize_countries',
        'disallowed_prize_regions',
        'edit_link',
    ]
    readonly_fields = ('edit_link',)
