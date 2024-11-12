"""Define serialization of the Django models into the REST framework."""

import contextlib
import logging
from collections import defaultdict
from contextlib import contextmanager
from functools import cached_property
from inspect import signature

from django.core.exceptions import NON_FIELD_ERRORS, ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail, ValidationError
from rest_framework.serializers import ListSerializer, as_serializer_error
from rest_framework.utils import model_meta
from rest_framework.validators import UniqueTogetherValidator

from tracker.api import messages
from tracker.models import Ad, Interstitial, Interview
from tracker.models.bid import Bid, DonationBid
from tracker.models.donation import Donation, Donor, Milestone
from tracker.models.event import Event, SpeedRun, Tag, Talent, VideoLink, VideoLinkType

log = logging.getLogger(__name__)


@contextmanager
def _coalesce_validation_errors(errors, ignored=None):
    """takes either a list, a dict, or a function that can potentially throw ValidationError"""
    ignored = set(ignored if ignored else [])
    if callable(errors):
        try:
            errors()
            errors = {}
        except (DjangoValidationError, ValidationError) as e:
            errors = as_serializer_error(e)
    elif isinstance(errors, list):
        if errors:
            errors = {NON_FIELD_ERRORS: errors}
        else:
            errors = {}
    try:
        yield
        other_errors = {}
    except (DjangoValidationError, ValidationError) as e:
        other_errors = as_serializer_error(e)
    if errors or other_errors:
        all_errors = {}
        for key, e in errors.items():
            o = other_errors.get(key, [] if isinstance(e, list) else {})
            if (isinstance(e, list) and isinstance(o, dict)) or (
                isinstance(e, dict) and isinstance(o, list)
            ):
                raise ValidationError(
                    {
                        key: 'Type conflict while processing validation errors, report this as a bug'
                    },
                    code='programming_error',
                )
            if isinstance(o, list):
                o = [oe for oe in o if key not in ignored or oe.code != 'required']
            if e or o:
                if isinstance(e, list):
                    all_errors[key] = e + o
                else:
                    # FIXME: this doesn't handle nested keys yet, but I don't have a good test case
                    all_errors[key] = {**e, **o}
        for key, o in other_errors.items():
            if isinstance(o, list):
                o = [oe for oe in o if key not in ignored or oe.code != 'required']
                if o:
                    all_errors.setdefault(key, []).extend(o)
            else:
                all_errors[key] = {**all_errors.get(key, {}), **o}
        assert all_errors, 'ended up with an empty error list after merging'
        raise ValidationError(all_errors)


class SerializerWithPermissionsMixin:
    def __init__(self, *args, with_permissions=(), **kwargs):
        if isinstance(with_permissions, str):
            with_permissions = (with_permissions,)
        self.permissions = tuple(with_permissions)
        super().__init__(*args, **kwargs)


class TrackerModelSerializer(serializers.ModelSerializer):
    def __init__(self, instance=None, exclude_from_clean=None, **kwargs):
        self.opts = self.Meta.model._meta.concrete_model._meta
        self.field_info = model_meta.get_field_info(self.Meta.model)
        self.nested_creates = getattr(self.Meta, 'nested_creates', [])
        self.exclude_from_clean = exclude_from_clean or []
        super().__init__(instance, **kwargs)

    def get_validators(self):
        validators = super().get_validators()
        # we do this ourselves and it causes weird issues elsewhere
        return tuple(
            v for v in validators if not isinstance(v, UniqueTogetherValidator)
        )

    def to_internal_value(self, data):
        request = self.context.get('request', None)
        errors = defaultdict(list)
        if request and request.method == 'POST':
            for key, value in data.items():
                field = self.fields.get(key, None)
                if (
                    (
                        isinstance(field, TrackerModelSerializer)
                        and isinstance(value, dict)
                    )
                    or (
                        isinstance(field, ListSerializer)
                        and isinstance(field.child, TrackerModelSerializer)
                        and any(isinstance(v, dict) for v in value)
                    )
                ) and key not in self.nested_creates:
                    errors[key].append(
                        ErrorDetail(
                            messages.NO_NESTED_CREATES,
                            code=messages.NO_NESTED_CREATES_CODE,
                        )
                    )
            for key in errors:
                data.pop(key, None)
        with _coalesce_validation_errors(errors, ignored=errors.keys()):
            return super().to_internal_value(data)

    def validate(self, attrs):
        if isinstance(attrs, dict):
            exclude = (
                tuple(self.exclude_from_clean)
                + tuple(getattr(self.Meta, 'exclude_from_clean', []))
                + tuple(
                    # TODO: figure this out dynamically?
                    getattr(self.Meta, 'exclude_from_clean_nested', [])
                    if self.root != self
                    else []
                )
            )
            set_attrs = {
                attr: value
                for attr, value in attrs.items()
                if not isinstance(
                    self.fields.get(attr, None),
                    (serializers.ManyRelatedField, serializers.ListSerializer),
                )
            }
            if self.partial:
                temp = self.Meta.model.objects.get(pk=self.instance.pk)
                for attr, value in set_attrs.items():
                    setattr(temp, attr, value)
            else:
                temp = self.Meta.model(**set_attrs)
            with _coalesce_validation_errors(lambda: temp.full_clean(exclude=exclude)):
                if self.instance:
                    invalid_updates = [k for k in attrs if k in self.nested_creates]
                    if invalid_updates:
                        raise ValidationError(
                            {k: messages.NO_NESTED_UPDATES for k in invalid_updates},
                            code=messages.NO_NESTED_UPDATES_CODE,
                        )
        return super().validate(attrs)

    def _pop_nested(self, validated_data):
        nested = {
            k: (
                next(
                    # TODO: change to r.accessor_name when 4.x is no longer supported
                    r
                    for r in self.opts.related_objects
                    if r.get_accessor_name() == k
                ).remote_field.name,
                validated_data.pop(k),
            )
            for k in list(validated_data.keys())
            if k in self.nested_creates
        }
        m2m = {
            k: validated_data.pop(k)
            for k in list(validated_data.keys())
            if k in self.field_info.forward_relations
            and self.field_info.forward_relations[k].to_many
        }
        return nested, m2m

    def _handle_nested(self, instance, nested, m2m):
        for attr, (accessor, value) in nested.items():
            assert isinstance(self.fields[attr], serializers.ListSerializer)
            value = self.fields[attr].to_internal_value(value)
            for v in value:
                v[accessor] = instance
            self.fields[attr].create(value)
        for attr, value in m2m.items():
            assert isinstance(
                self.fields[attr],
                (serializers.ManyRelatedField, serializers.ListSerializer),
            )
            getattr(instance, attr).set(self.fields[attr].to_internal_value(value))

    def create(self, validated_data):
        nested, m2m = self._pop_nested(validated_data)
        instance = super().create(validated_data)
        self._handle_nested(instance, nested, m2m)
        return instance

    def update(self, instance, validated_data):
        nested, m2m = self._pop_nested(validated_data)
        assert (
            len(nested) == 0
        ), 'got nested writes in .update(), should have been caught by validate()'
        instance = super().update(instance, validated_data)
        self._handle_nested(instance, {}, m2m)
        return instance


class PrimaryOrNaturalKeyLookup:
    default_error_messages = {
        messages.INVALID_PK_CODE: messages.INVALID_PK,
        messages.INVALID_NATURAL_KEY_CODE: messages.INVALID_NATURAL_KEY,
        messages.INVALID_NATURAL_KEY_LENGTH_CODE: messages.INVALID_NATURAL_KEY_LENGTH,
        messages.INVALID_LOOKUP_TYPE_CODE: messages.INVALID_LOOKUP_TYPE,
    }

    class Meta:
        model = None

    def __init__(self, *args, queryset=None, **kwargs):
        assert (
            self.Meta.model is not None
        ), 'Meta.model cannot be None when using PrimaryOrNaturalKeyLookup'
        self.queryset = queryset or self.Meta.model.objects
        self.get_by_natural_key = getattr(
            self.Meta.model.objects, 'get_by_natural_key', None
        )
        super().__init__(*args, **kwargs)

    def __new__(cls, *args, **kwargs):
        if kwargs.pop('many', False):
            assert hasattr(cls, 'many_init')
            return cls.many_init(*args, **kwargs)
        return super().__new__(cls, *args, **kwargs)

    def get_choices(self, cutoff=None):
        # FIXME: makes the browsable API happy, see: https://github.com/encode/django-rest-framework/issues/5141
        return {m.id: m.name for m in self.queryset.all()}

    def to_internal_value(self, data):
        if isinstance(data, dict):
            return super().to_internal_value(data)
        elif isinstance(data, int):
            try:
                return self.queryset.get(pk=data)
            except ObjectDoesNotExist:
                self.fail(messages.INVALID_PK_CODE, pk=data)
        elif callable(self.get_by_natural_key) and isinstance(data, (list, str)):
            if not isinstance(data, list):
                key = [data]
            else:
                key = data
            sig = signature(self.get_by_natural_key)
            try:
                sig.bind(*key)
            except TypeError:
                self.fail(
                    messages.INVALID_NATURAL_KEY_LENGTH_CODE,
                    expected=len(sig.parameters),
                    actual=len(key),
                )
            try:
                return self.get_by_natural_key(*key)
            except ObjectDoesNotExist:
                self.fail(messages.INVALID_NATURAL_KEY_CODE, natural_key=data)
        elif isinstance(data, self.Meta.model):
            return data
        else:
            self.fail(messages.INVALID_LOOKUP_TYPE_CODE)


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


class EventNestedSerializerMixin:
    event_move = False

    def __init__(self, *args, event_pk=None, **kwargs):
        # FIXME: figure out a more elegant way to pass this in tests since they're the only
        #  ones that use it any more
        super().__init__(*args, **kwargs)
        self.event_pk = event_pk
        # without this check, patching by event url doesn't work
        self.event_in_url = (
            view := self.context.get('view', None)
        ) and 'event_pk' in view.kwargs

    def get_fields(self):
        fields = super().get_fields()
        if self.instance and not self.event_move:
            fields['event'].read_only = True
        return fields

    def get_event_pk(self):
        return self.event_pk or (
            (view := self.context.get('view', None))
            and ((pk := view.kwargs.get('event_pk', None)) is not None)
            and int(pk)
        )

    def get_event(self):
        return (event_pk := self.get_event_pk()) and Event.objects.filter(
            pk=event_pk
        ).first()

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if self.get_event_pk() and 'event' in ret:
            del ret['event']
        return ret

    def to_internal_value(self, data):
        if (
            isinstance(data, dict)
            and 'event' not in data
            and (event_pk := self.get_event_pk())
        ):
            data['event'] = event_pk
        value = super().to_internal_value(data)
        return value

    def validate(self, data):
        # TODO: validate_event would not be called because the field is read-only in this case,
        #  so this is how we make this error case more explicit for now
        if (
            not self.event_move
            and self.instance
            and ('event' in getattr(self, 'initial_data', {}) and not self.event_in_url)
        ):
            raise ValidationError(
                {'event': messages.EVENT_READ_ONLY}, code=messages.EVENT_READ_ONLY_CODE
            )
        return super().validate(data)


class BidSerializer(
    SerializerWithPermissionsMixin, EventNestedSerializerMixin, TrackerModelSerializer
):
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
            'estimate',
            'close_at',
            'post_run',
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
        # check for any of the sufficient permissions
        return instance.state in Bid.PUBLIC_STATES or (
            self.include_hidden
            and (
                {'tracker.view_hidden_bid', 'tracker.view_bid', 'tracker.change_bid'}
                & set(self.permissions)
            )
        )

    def to_representation(self, instance, child=False):
        # final check
        assert self._has_permission(
            instance
        ), f'tried to serialize a hidden bid without permission {self.include_hidden} {self.permissions}'
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
            if 'event' in data:
                del data['event']
            del data['speedrun']
            del data['parent']
            del data['pinned']
            del data['chain']
            if not instance.chain:
                del data['goal']
        if instance.chain or child:
            del data['close_at']
            del data['post_run']
            del data['repeat']
            del data['allowuseroptions']
        return data

    def get_fields(self):
        fields = super().get_fields()
        if 'event' in fields:
            fields['event'].required = False
        fields['speedrun'].required = False
        return fields

    def to_internal_value(self, data):
        parent = None
        errors = defaultdict(list)
        if 'parent' in data:
            try:
                parent = Bid.objects.filter(pk=data['parent']).first()
            except ValueError:
                errors['parent'].append(
                    ErrorDetail(messages.INVALID_LOOKUP_TYPE, code='incorrect_type')
                )
        with _coalesce_validation_errors(errors):
            value = super().to_internal_value(data)
            if parent:
                value['parent'] = parent
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


class DonationBidSerializer(SerializerWithPermissionsMixin, TrackerModelSerializer):
    type = ClassNameField()
    bid_name = serializers.SerializerMethodField()
    bid_state = serializers.SerializerMethodField()

    class Meta:
        model = DonationBid
        fields = ('type', 'id', 'donation', 'bid', 'bid_name', 'bid_state', 'amount')

    def get_bid_name(self, donation_bid: DonationBid):
        return donation_bid.bid.fullname()

    def get_bid_state(self, donation_bid: DonationBid):
        return donation_bid.bid.state

    def _has_permission(self, instance):
        return (
            any(
                f'tracker.{p}' in self.permissions
                for p in ('view_hidden_bid', 'change_bid', 'view_bid')
            )
            or instance.bid.state in Bid.PUBLIC_STATES
        )

    def to_representation(self, instance):
        # final check
        assert self._has_permission(
            instance
        ), f'tried to serialize a hidden donation bid without permission {self.permissions}'
        return super().to_representation(instance)


class DonationSerializer(SerializerWithPermissionsMixin, serializers.ModelSerializer):
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
        if donation.anonymous():
            return Donor.ANONYMOUS
        if donation.requestedalias is None:
            return Donor.ANONYMOUS

        return donation.requestedalias


class EventSerializer(PrimaryOrNaturalKeyLookup, TrackerModelSerializer):
    type = ClassNameField()
    timezone = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    donation_count = serializers.SerializerMethodField()

    def __init__(self, *args, with_totals=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.with_totals = with_totals

    class Meta:
        model = Event
        fields = (
            'type',
            'id',
            'short',
            'name',
            'amount',
            'donation_count',
            'paypalcurrency',
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


class TalentSerializer(
    PrimaryOrNaturalKeyLookup,
    TrackerModelSerializer,
    SerializerWithPermissionsMixin,
    EventNestedSerializerMixin,
):
    type = ClassNameField()

    class Meta:
        model = Talent
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


class VideoLinkSerializer(TrackerModelSerializer):
    class LinkTypeSerializer(PrimaryOrNaturalKeyLookup, TrackerModelSerializer):
        def to_representation(self, instance):
            return instance.name

        class Meta:
            model = VideoLinkType
            fields = ('name',)

    link_type = LinkTypeSerializer()

    class Meta:
        model = VideoLink
        exclude_from_clean_nested = ('run',)
        fields = (
            'id',
            'link_type',
            'url',
        )


class TagField(serializers.RelatedField):
    default_error_messages = {
        messages.INVALID_NATURAL_KEY_CODE: messages.INVALID_NATURAL_KEY,
    }

    def __init__(self, *, allow_create=False, **kwargs):
        super().__init__(**kwargs)
        self.allow_create = allow_create

    def get_queryset(self):
        return Tag.objects.all()

    def to_representation(self, value):
        return value.name

    # TODO: maybe? if we run across other models where this makes sense to allow implied creation,
    #  generalize this solution a bit
    def to_internal_value(self, data):
        try:
            if isinstance(data, str):
                return Tag.objects.get_by_natural_key(data)
            elif isinstance(data, Tag):
                return data
            raise TypeError(f'expected Tag or str, got {type(data)}')
        except ObjectDoesNotExist:
            if self.allow_create:
                tag = Tag(name=data)
                tag.full_clean()
                tag.save()
                return tag
            else:
                self.fail(messages.INVALID_NATURAL_KEY_CODE, natural_key=data)


class SpeedRunSerializer(
    PrimaryOrNaturalKeyLookup,
    SerializerWithPermissionsMixin,
    EventNestedSerializerMixin,
    TrackerModelSerializer,
):
    type = ClassNameField()
    event = EventSerializer()
    runners = TalentSerializer(many=True)
    hosts = TalentSerializer(many=True, required=False)
    commentators = TalentSerializer(many=True, required=False)
    video_links = VideoLinkSerializer(many=True, required=False)
    priority_tag = TagField(allow_null=True, required=False, allow_create=True)
    tags = TagField(many=True, required=False, allow_create=True)

    class Meta:
        model = SpeedRun
        fields = (
            'type',
            'id',
            'event',
            'name',
            'display_name',
            'twitch_name',
            'description',
            'category',
            'coop',
            'onsite',
            'console',
            'release_year',
            'runners',
            'hosts',
            'commentators',
            'starttime',
            'endtime',
            'order',
            'run_time',
            'setup_time',
            'anchor_time',
            'tech_notes',
            'video_links',
            'priority_tag',
            'tags',
        )
        nested_creates = ('video_links',)
        extra_kwargs = {
            # TODO: almost assuredly a bug in DRF, see: https://github.com/encode/django-rest-framework/discussions/9538
            'order': {'default': None, 'required': False}
        }

    def __init__(self, *args, with_tech_notes=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.with_tech_notes = with_tech_notes

    def _has_tech_notes_permission(self):
        # TODO: maybe put this in a helper
        return {
            'tracker.can_view_tech_notes',
            'tracker.add_speedrun',
            'tracker.change_speedrun',
            'tracker.view_speedrun',
        } & set(self.permissions)

    def to_representation(self, instance):
        assert (
            not self.with_tech_notes or self._has_tech_notes_permission()
        ), 'tried to serialize a run with tech notes without permission'
        return super().to_representation(instance)

    def to_internal_value(self, data):
        last = isinstance(data, dict) and data.get('order', None) == 'last'
        if last:
            del data['order']
        value = super().to_internal_value(data)
        if last:
            run = value['event'].speedrun_set.exclude(order=None).last()
            if run:
                value['order'] = run.order + 1
            else:
                value['order'] = 1
        return value

    def get_fields(self):
        fields = super().get_fields()
        if not self.with_tech_notes and 'tech_notes' in fields:
            del fields['tech_notes']
        return fields


class InterstitialSerializer(EventNestedSerializerMixin, TrackerModelSerializer):
    type = ClassNameField()
    event = EventSerializer()
    tags = TagField(many=True, required=False, allow_create=True)
    anchor = SpeedRunSerializer(required=False)

    class Meta:
        fields = (
            'type',
            'id',
            'event',
            'anchor',
            'order',
            'suborder',
            'tags',
        )

    def to_internal_value(self, data):
        errors = defaultdict(list)
        if anchor := data.get('anchor', None):
            if 'event' in data:
                errors['event'].append(
                    ErrorDetail(messages.ANCHOR_FIELD, code=messages.ANCHOR_FIELD_CODE)
                )
            if 'order' in data:
                errors['order'].append(
                    ErrorDetail(messages.ANCHOR_FIELD, code=messages.ANCHOR_FIELD_CODE)
                )

            with contextlib.suppress(ValidationError):
                if anchor := SpeedRunSerializer().to_internal_value(anchor):
                    data['anchor'] = anchor.id
                    data['event'] = anchor.event_id
                    if anchor.order:
                        data['order'] = anchor.order
                    else:
                        errors['anchor'].append(
                            ErrorDetail(
                                messages.INVALID_ANCHOR,
                                code=messages.INVALID_ANCHOR_CODE,
                            )
                        )
        if last := data.get('suborder', None) == 'last':
            data['suborder'] = 10000  # TODO: horrible lie to silence the validation
        with _coalesce_validation_errors(errors):
            value = super().to_internal_value(data)
        if last:
            if interstitial := Interstitial.objects.filter(
                event=value['event'],
                order=value['order'],
            ).last():
                value['suborder'] = interstitial.suborder + 1
            else:
                data['suborder'] = 1

        return value


class AdSerializer(InterstitialSerializer):
    class Meta:
        model = Ad
        fields = InterstitialSerializer.Meta.fields + (
            'sponsor_name',
            'ad_name',
            'ad_type',
            'filename',
            'blurb',
        )


class InterviewSerializer(InterstitialSerializer):
    class Meta:
        model = Interview
        fields = InterstitialSerializer.Meta.fields + (
            'social_media',
            'interviewers',
            'topic',
            'public',
            'prerecorded',
            'producer',
            'length',
            'subjects',
            'camera_operator',
        )


class MilestoneSerializer(
    SerializerWithPermissionsMixin, EventNestedSerializerMixin, TrackerModelSerializer
):
    type = ClassNameField()
    event = EventSerializer()

    class Meta:
        model = Milestone
        fields = (
            'type',
            'id',
            'event',
            'start',
            'amount',
            'name',
            'visible',
            'description',
            'short_description',
        )
