"""Define serialization of the Django models into the REST framework."""

import logging
from collections import defaultdict
from contextlib import contextmanager

try:
    from functools import cached_property
except ImportError:
    from backports.cached_property import cached_property

from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from tracker.models.bid import Bid, DonationBid
from tracker.models.donation import Donation
from tracker.models.event import Event, Headset, Runner, SpeedRun

log = logging.getLogger(__name__)


@contextmanager
def _coalesce_validation_errors(errors):
    try:
        yield
    except ValidationError as e:
        if isinstance(errors, list):
            errors = {NON_FIELD_ERRORS: errors}
        errors = e.update_error_dict(errors)
    if errors:
        raise ValidationError(errors)


class WithPermissionsMixin:
    def __init__(self, instance, *, with_permissions=(), **kwargs):
        self.permissions = tuple(with_permissions)
        super().__init__(instance, **kwargs)


class TrackerModelSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        if not self.partial:
            self.Meta.model(**attrs).clean()
        else:
            temp = self.Meta.model.objects.get(pk=self.instance.pk)
            for attr, value in attrs.items():
                if attr in self.fields:
                    setattr(temp, attr, value)
            temp.clean()
        return super().validate(attrs)


class ClassNameField(serializers.Field):
    """Provide the class name as a lowercase string, to provide it as an extra field.

    Borrowed from the DRF docs.
    """

    def __init__(self, required=False, read_only=True, *args, **kwargs):
        super().__init__(*args, required=required, read_only=read_only, **kwargs)

    def get_attribute(self, obj):
        # We pass the object instance onto `to_representation`,
        # not just the field attribute.
        return obj

    def to_representation(self, obj):
        """Serialize the object's class name."""
        return obj.__class__.__name__.lower()


class BidSerializer(WithPermissionsMixin, TrackerModelSerializer):
    type = ClassNameField()

    def __init__(self, *args, include_hidden=False, feed=None, tree=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.include_hidden = include_hidden
        self.feed = feed
        self.tree = tree

    class Meta:
        model = Bid
        fields = (
            'type',
            'id',
            'name',
            'event',
            'speedrun',
            'state',
            'parent',
            'description',
            'shortdescription',
            'goal',
            'chain_goal',
            'chain_remaining',
            'total',
            'count',
            'repeat',
            'chain',
            'istarget',
            'pinned',
            'allowuseroptions',
            'option_max_length',
            'revealedtime',
            'level',
        )

    @cached_property
    def _tree(self):
        # for a tree list view we want to cache all the possible descendants
        if isinstance(self.instance, list):
            return Bid.objects.filter(
                pk__in=(b.pk for b in self.instance)
            ).get_descendants()
        else:
            return self.instance.get_descendants()

    def _find_descendants(self, parent):
        for child in self._tree:
            if child.parent_id == parent.id:
                yield child
                yield from self._find_descendants(child)

    def _find_children(self, parent):
        yield from (child for child in self._tree if child.parent_id == parent.id)

    def _has_permission(self, instance):
        return instance.state in Bid.PUBLIC_STATES or (
            self.include_hidden and 'tracker.view_hidden_bid' in self.permissions
        )

    def to_representation(self, instance, child=False):
        # final check
        assert self._has_permission(
            instance
        ), f'tried to serialized a hidden bid without permission {self.include_hidden} {self.permissions}'
        data = super().to_representation(instance)
        if self.tree:
            if instance.chain:
                if instance.istarget:
                    data['chain_steps'] = [
                        self.to_representation(step, child=True)
                        for step in self._find_descendants(instance)
                    ]
            elif not instance.istarget:
                data['options'] = [
                    self.to_representation(option, child=True)
                    for option in self._find_children(instance)
                    if self._has_permission(option)  # children might be pending/denied
                ]
        if not instance.chain:
            del data['chain_goal']
            del data['chain_remaining']
        if not instance.allowuseroptions:
            del data['option_max_length']
        if child:
            del data['event']
            del data['speedrun']
            del data['parent']
            del data['pinned']
            del data['chain']
            if not instance.chain:
                del data['goal']
        if instance.chain or child:
            del data['repeat']
            del data['allowuseroptions']
        return data

    def get_fields(self):
        fields = super().get_fields()
        fields['event'].required = False
        fields['speedrun'].required = False
        return fields

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if 'parent' in data:
            try:
                value['parent'] = Bid.objects.filter(pk=data['parent']).first()
            except ValueError:
                # nonsense values could cause a vague error message here, but if you feed garbage to
                #  my API you should expect to get garbage back
                value['parent'] = None
        return value

    def validate(self, attrs):
        errors = defaultdict(list)
        if 'parent' in attrs:
            # only allow parent setting on creation
            if self.instance is None:
                if attrs['parent'] is None:
                    errors['parent'].append(_('Parent does not exist.'))
            elif self.instance.parent != attrs['parent']:
                errors['parent'].append(_('Can only set parent on new bids.'))
        with _coalesce_validation_errors(errors):
            return super().validate(attrs)


class DonationBidSerializer(serializers.ModelSerializer):
    type = ClassNameField()
    bid_name = serializers.SerializerMethodField()

    class Meta:
        model = DonationBid
        fields = ('type', 'id', 'donation', 'bid', 'bid_name', 'amount')

    def get_bid_name(self, donation_bid: DonationBid):
        return donation_bid.bid.fullname()


class DonationSerializer(WithPermissionsMixin, serializers.ModelSerializer):
    type = ClassNameField()
    donor_name = serializers.SerializerMethodField()
    bids = DonationBidSerializer(many=True, read_only=True)

    class Meta:
        model = Donation
        fields = (
            'type',
            'id',
            'donor',
            'donor_name',
            'event',
            'domain',
            'transactionstate',
            'readstate',
            'commentstate',
            'amount',
            'currency',
            'timereceived',
            'comment',
            'commentlanguage',
            'pinned',
            'bids',
            'modcomment',
        )

    def get_fields(self):
        fields = super().get_fields()
        if 'tracker.change_donation' not in self.permissions:
            del fields['modcomment']

        return fields

    def get_donor_name(self, donation: Donation):
        if donation.donor is not None:
            return donation.donor.full_alias
        if donation.requestedvisibility != 'ANON':
            return donation.requestedalias
        return '(Anonymous)'


class EventSerializer(serializers.ModelSerializer):
    type = ClassNameField()
    timezone = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    donation_count = serializers.SerializerMethodField()

    def __init__(self, instance=None, *, with_totals=False, **kwargs):
        self.with_totals = with_totals
        super().__init__(instance, **kwargs)

    class Meta:
        model = Event
        fields = (
            'type',
            'id',
            'short',
            'name',
            'amount',
            'donation_count',
            'hashtag',
            'datetime',
            'timezone',
            'use_one_step_screening',
        )

    def get_fields(self):
        fields = super().get_fields()
        if not self.with_totals:
            del fields['amount']
            del fields['donation_count']

        return fields

    def get_timezone(self, obj):
        return str(obj.timezone)

    def get_donation_count(self, obj):
        if not self.with_totals:
            return None

        return obj.donation_count

    def get_amount(self, obj):
        if not self.with_totals:
            return None

        return obj.amount


class RunnerSerializer(serializers.ModelSerializer):
    type = ClassNameField()

    class Meta:
        model = Runner
        fields = (
            'type',
            'id',
            'name',
            'stream',
            'twitter',
            'youtube',
            'platform',
            'pronouns',
        )


class HeadsetSerializer(serializers.ModelSerializer):
    type = ClassNameField()

    class Meta:
        model = Headset
        fields = (
            'type',
            'id',
            'name',
            'pronouns',
        )


class SpeedRunSerializer(serializers.ModelSerializer):
    type = ClassNameField()
    event = EventSerializer()
    runners = RunnerSerializer(many=True)
    hosts = HeadsetSerializer(many=True)
    commentators = HeadsetSerializer(many=True)

    class Meta:
        model = SpeedRun
        fields = (
            'type',
            'id',
            'event',
            'name',
            'display_name',
            'description',
            'category',
            'console',
            'runners',
            'hosts',
            'commentators',
            'starttime',
            'endtime',
            'order',
            'run_time',
        )
