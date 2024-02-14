from django.contrib import admin
from django.utils.safestring import mark_safe

from tracker import models, viewutil

from .forms import DonationBidForm, DonorPrizeEntryForm, PrizeForm, PrizeWinnerForm


class CustomStackedInline(admin.StackedInline):
    # Adds an link that lets you edit an in-line linked object
    def edit_link(self, instance):
        if instance.id is not None:
            url = viewutil.admin_url(instance)
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
    extra = 0
    readonly_fields = (
        'total',
        'edit_link',
    )
    ordering = ('-total', 'name')

    def get_fieldsets(self, request, obj=None):
        return [
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


class BidOptionInline(BidInline):
    verbose_name_plural = 'Options'
    verbose_name = 'Option'
    fk_name = 'parent'

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        if obj and obj.allowuseroptions:
            formset.form.base_fields['state'].choices = [
                c
                for c in formset.form.base_fields['state'].choices
                if c[0] in [obj.state, 'PENDING', 'DENIED']
            ]
        return formset

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        fieldsets[0][1]['fields'].remove('goal')
        if not (obj and obj.allowuseroptions):
            fieldsets[0][1]['fields'].remove('state')
        return fieldsets


class BidDependentsInline(BidInline):
    verbose_name_plural = 'Dependent Bids'
    verbose_name = 'Dependent Bid'
    fk_name = 'biddependency'

    def has_add_permission(self, request, obj):
        return False

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        fieldsets[0][1]['fields'].remove('goal')
        return fieldsets


class BidChainedInline(BidInline):
    verbose_name = 'Chained Bid'
    fk_name = 'parent'
    max_num = 1
    readonly_fields = BidInline.readonly_fields + ('chain_goal', 'chain_remaining')

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        fieldsets[0][1]['fields'].remove('istarget')
        fieldsets[0][1]['fields'].extend(('chain_goal', 'chain_remaining'))
        return fieldsets


class EventBidInline(BidInline):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
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


class VideoLinkInline(CustomStackedInline):
    model = models.VideoLink
    readonly_fields = ('edit_link',)
    extra = 1
