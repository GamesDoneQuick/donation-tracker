from django.contrib import admin
from django.utils.safestring import mark_safe

from tracker import models, viewutil


class CustomStackedInline(admin.StackedInline):
    def get_readonly_fields(self, request, obj=None):
        return tuple(super().get_readonly_fields(request, obj)) + ('edit_link',)

    def edit_link(self, instance):
        """
        Adds a link that lets you edit an in-line linked object
        """
        if instance.id is not None:
            url = viewutil.admin_url(instance)
            return mark_safe('<a href="{u}">Edit</a>'.format(u=url))
        else:
            return mark_safe('Not Saved Yet')


class DonationBidInline(CustomStackedInline):
    autocomplete_fields = ('bid',)
    model = models.DonationBid
    extra = 0
    max_num = 100


class BidInline(CustomStackedInline):
    model = models.Bid
    extra = 0
    readonly_fields = (
        'estimate',
        'total',
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
                        'estimate',
                        'total',
                        'edit_link',
                    ],
                },
            )
        ]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj and not obj.allowuseroptions:
            readonly_fields = readonly_fields + ('state',)
        return readonly_fields


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


class PrizeWinnerInline(CustomStackedInline):
    autocomplete_fields = ('winner', 'prize')
    model = models.PrizeWinner
    readonly_fields = ('winner_email',)
    extra = 0

    def winner_email(self, obj):
        return obj.winner.email


class DonorPrizeEntryInline(CustomStackedInline):
    autocomplete_fields = ('donor', 'prize')
    model = models.DonorPrizeEntry
    extra = 0


class VideoLinkInline(CustomStackedInline):
    model = models.VideoLink
    extra = 1
