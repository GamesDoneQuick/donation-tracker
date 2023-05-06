"""Define serialization of the Django models into the REST framework."""

import logging

from django.contrib.auth.models import User
from rest_framework import serializers

from tracker.models.bid import DonationBid
from tracker.models.donation import Donation, DonationProcessAction
from tracker.models.event import Event, Headset, Runner, SpeedRun

log = logging.getLogger(__name__)


class ClassNameField(serializers.Field):
    """Provide the class name as a lowercase string, to provide it as an extra field.

    Borrowed from the DRF docs.
    """

    def get_attribute(self, obj):
        # We pass the object instance onto `to_representation`,
        # not just the field attribute.
        return obj

    def to_representation(self, obj):
        """Serialize the object's class name."""
        return obj.__class__.__name__.lower()


class UserSerializer(serializers.ModelSerializer):
    type = ClassNameField()

    class Meta:
        model = User
        fields = ('type', 'id', 'username')


class DonationBidSerializer(serializers.ModelSerializer):
    type = ClassNameField()
    bid_name = serializers.SerializerMethodField()

    class Meta:
        model = DonationBid
        fields = ('type', 'id', 'donation', 'bid', 'bid_name', 'amount')

    def get_bid_name(self, donation_bid: DonationBid):
        return donation_bid.bid.fullname()


class DonationSerializer(serializers.ModelSerializer):
    type = ClassNameField()
    donor_name = serializers.SerializerMethodField()
    bids = DonationBidSerializer(many=True, read_only=True)

    def __init__(self, instance=None, *, with_permissions=None, **kwargs):
        self.permissions = with_permissions or []
        super().__init__(instance, **kwargs)

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


class DonationProcessActionSerializer(serializers.ModelSerializer):
    type = ClassNameField()
    actor = UserSerializer()
    donation = DonationSerializer()
    donation_id = serializers.SerializerMethodField()
    originating_action = serializers.SerializerMethodField()

    def __init__(
        self,
        instance=None,
        *,
        with_donation: bool = True,
        with_originating_action: bool = True,
        **kwargs,
    ):
        self.with_donation = with_donation
        self.with_originating_action = with_originating_action
        super().__init__(instance, **kwargs)

    class Meta:
        model = DonationProcessAction
        fields = (
            'type',
            'id',
            'actor',
            'donation',
            'donation_id',
            'from_state',
            'to_state',
            'occurred_at',
            'originating_action',
        )

    def get_fields(self):
        fields = super().get_fields()
        if not self.with_donation:
            del fields['donation']
        if not self.with_originating_action:
            del fields['originating_action']

        return fields

    def get_originating_action(self, obj):
        if obj.originating_action is None:
            return None

        return DonationProcessActionSerializer(
            obj.originating_action,
            with_donation=False,
            with_originating_action=False,
        ).data

    def get_donation_id(self, obj):
        return obj.donation.id


class EventSerializer(serializers.ModelSerializer):
    type = ClassNameField()
    timezone = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = (
            'type',
            'id',
            'short',
            'name',
            'hashtag',
            'datetime',
            'timezone',
            'use_one_step_screening',
        )

    def get_timezone(self, obj):
        return str(obj.timezone)


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
