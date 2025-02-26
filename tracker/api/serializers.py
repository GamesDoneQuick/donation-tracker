"""Define serialization of the Django models into the REST framework."""

import contextlib
import datetime
import logging
from collections import defaultdict
from contextlib import contextmanager
from decimal import Decimal
from functools import cached_property
from inspect import signature

from django.core.exceptions import NON_FIELD_ERRORS, ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail, ValidationError
from rest_framework.fields import DateTimeField, DecimalField
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import ListSerializer, as_serializer_error
from rest_framework.utils import model_meta
from rest_framework.validators import UniqueTogetherValidator

from tracker.api import messages
from tracker.models import Prize, Tag
from tracker.models.bid import Bid, DonationBid
from tracker.models.country import Country, CountryRegion
from tracker.models.donation import Donation, DonationGroup, Donor, Milestone
from tracker.models.event import Event, SpeedRun, Talent, VideoLink, VideoLinkType
from tracker.models.interstitial import Ad, Interstitial, Interview
from tracker.models.tag import AbstractTag

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
    _perm_cache = []

    def __init__(self, *args, with_permissions=(), **kwargs):
        from tracker import settings

        if isinstance(with_permissions, str):
            with_permissions = (with_permissions,)
        self.permissions = tuple(with_permissions)
        if settings.DEBUG:
            from django.contrib.auth.models import Permission

            for permission in self.permissions:
                if not SerializerWithPermissionsMixin._perm_cache:
                    SerializerWithPermissionsMixin._perm_cache = [
                        f'{p.content_type.app_label}.{p.codename}'
                        for p in Permission.objects.select_related('content_type')
                    ]
                assert (
                    permission in SerializerWithPermissionsMixin._perm_cache
                ), f'nonsense permission `{permission}`'

        super().__init__(*args, **kwargs)

    @property
    def root_permissions(self):
        if (permissions := getattr(self.root, 'permissions', None)) is not None:
            return permissions
        return getattr(self.root.child, 'permissions', self.permissions)


class TrackerModelSerializer(serializers.ModelSerializer):
    def __init__(self, instance=None, exclude_from_clean=None, **kwargs):
        self.opts = self.Meta.model._meta.concrete_model._meta
        self.field_info = model_meta.get_field_info(self.Meta.model)
        self.nested_creates = getattr(self.Meta, 'nested_creates', [])
        self.exclude_from_clean = exclude_from_clean or []
        super().__init__(instance, **kwargs)

    @property
    def is_root(self):
        return self.root is self or (
            isinstance(self.root, ListSerializer) and self.root.child is self
        )

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            if isinstance(field, DecimalField):
                field.coerce_to_string = False
        if not self.is_root:
            for field in getattr(self.Meta, 'exclude_from_nested', []):
                fields.pop(field, None)
        return fields

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

    def _ensure_serializable(self, data):
        if isinstance(data, Decimal):
            return float(data)
        elif isinstance(data, datetime.datetime):
            return DateTimeField().to_representation(data)
        elif isinstance(data, dict):
            return {k: self._ensure_serializable(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._ensure_serializable(v) for v in data]
        else:
            return data

    def to_representation(self, instance):
        return self._ensure_serializable(super().to_representation(instance))

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


class AbstractTagField(serializers.RelatedField):
    default_error_messages = {
        messages.INVALID_NATURAL_KEY_CODE: messages.INVALID_NATURAL_KEY,
    }

    def __init__(self, *, model=None, allow_create=False, queryset=None, **kwargs):
        assert model is not None and issubclass(
            model, AbstractTag
        ), 'must provide a subclass of AbstractTag'
        self.model = model
        self.queryset = queryset or model.objects
        super().__init__(**kwargs)
        self.allow_create = allow_create

    def to_representation(self, value):
        return value.name

    # TODO: maybe? if we run across other models where this makes sense to allow implied creation,
    #  generalize this solution a bit
    def to_internal_value(self, data):
        try:
            if isinstance(data, str):
                return self.model.objects.get_by_natural_key(data)
            elif isinstance(data, self.model):
                return data
            raise TypeError(f'expected {type(self.model)} or str, got {type(data)}')
        except ObjectDoesNotExist:
            if self.allow_create:
                tag = self.model.objects.create(name=data)
                tag.full_clean()
                tag.save()
                return tag
            else:
                self.fail(messages.INVALID_NATURAL_KEY_CODE, natural_key=data)


class CountrySerializer(PrimaryOrNaturalKeyLookup, TrackerModelSerializer):
    type = ClassNameField()

    class Meta:
        model = Country
        fields = (
            'type',
            'name',
            'alpha2',
            'alpha3',
            'numeric',
        )

    def to_representation(self, instance):
        if self.is_root:
            return super().to_representation(instance)
        else:
            return instance.alpha3


class CountryRegionSerializer(PrimaryOrNaturalKeyLookup, TrackerModelSerializer):
    type = ClassNameField()
    country = CountrySerializer()

    class Meta:
        model = CountryRegion
        fields = (
            'type',
            'id',
            'name',
            'country',
        )

    def to_representation(self, instance):
        if self.is_root:
            return super().to_representation(instance)
        else:
            return [instance.name, instance.country.alpha3]


class EventNestedSerializerMixin:
    event_move = False

    def __init__(self, *args, event_pk=None, **kwargs):
        super().__init__(*args, **kwargs)
        view = self.context.get('view', None)
        assert (
            view is None or event_pk is None
        ), 'event_pk should only be passed by tests when the view is not directly available'
        self.event_pk = (
            (((pk := view.kwargs.get('event_pk', None)) and int(pk)) or None)
            if view is not None
            else event_pk
        )
        # without this check, patching by event url doesn't work
        self.event_in_url = view and 'event_pk' in view.kwargs

    def get_fields(self):
        fields = super().get_fields()
        if self.instance and not self.event_move and 'event' in 'fields':
            fields['event'].read_only = True
        return fields

    def get_event(self):
        return self.event_pk and Event.objects.filter(pk=self.event_pk).first()

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if self.event_pk:
            ret.pop('event', None)
        return ret

    def to_internal_value(self, data):
        if isinstance(data, dict) and 'event' not in data and self.event_pk:
            data['event'] = self.event_pk
        value = super().to_internal_value(data)
        return value

    def validate(self, data):
        def _check_event():
            # TODO: validate_event would not be called because the field is read-only in this case,
            #  so this is how we make this error case more explicit for now
            if (
                not self.event_move
                and self.instance
                and (
                    'event' in getattr(self, 'initial_data', {})
                    and not self.event_in_url
                )
            ):
                raise ValidationError(
                    {'event': messages.EVENT_READ_ONLY},
                    code=messages.EVENT_READ_ONLY_CODE,
                )

        with _coalesce_validation_errors(_check_event):
            return super().validate(data)


class BidSerializer(
    SerializerWithPermissionsMixin, EventNestedSerializerMixin, TrackerModelSerializer
):
    type = ClassNameField()
    bid_type = serializers.SerializerMethodField()
    event_move = True

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
            'bid_type',
            'name',
            'event',
            'speedrun',
            'parent',
            'state',
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
            'accepted_number',
            'istarget',
            'allowuseroptions',
            'option_max_length',
            'revealedtime',
            'level',
        )

    def get_bid_type(self, instance):
        if instance.chain:
            return 'challenge'
        if instance.istarget:
            if instance.parent_id is None:
                return 'challenge'
            else:
                return 'option'
        return 'choice'

    @cached_property
    def _tree(self):
        # for a tree list view we want to cache all the possible descendants
        if isinstance(self.instance, Bid):
            return self.instance.get_descendants()
        else:
            return (
                Bid.objects.filter(pk__in=(b.pk for b in self.instance))
                .only('pk')
                .get_descendants()
            )

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
                {'tracker.view_bid', 'tracker.change_bid'} & set(self.root_permissions)
            )
        )

    def to_representation(self, instance, child=False):
        # final check
        assert self._has_permission(
            instance
        ), f'tried to serialize a hidden bid without permission {self.include_hidden} {self.root_permissions}'
        data = super().to_representation(instance)
        if self.tree:
            assert (
                instance.parent_id is None or child
            ), f'tried to serialize a bid tree from the middle {instance.parent_id}'
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
            del data['level']
        if not instance.chain:
            del data['chain_goal']
            del data['chain_remaining']
        if not instance.allowuseroptions:
            del data['option_max_length']
        if self.tree or child:
            del data['parent']
        if child:
            if 'event' in data:
                del data['event']
            del data['speedrun']
            del data['chain']
            if not instance.chain:
                del data['close_at']
                del data['post_run']
                del data['goal']
        if instance.chain or instance.parent_id:
            del data['repeat']
        if instance.chain or instance.parent_id or instance.istarget:
            del data['accepted_number']
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
    bid_count = serializers.SerializerMethodField()
    bid_total = serializers.SerializerMethodField()

    class Meta:
        model = DonationBid
        fields = (
            'type',
            'id',
            'donation',
            'bid',
            'bid_name',
            'bid_state',
            'bid_count',
            'bid_total',
            'amount',
        )

    def get_bid_name(self, donation_bid: DonationBid):
        return donation_bid.bid.fullname()

    def get_bid_state(self, donation_bid: DonationBid):
        return donation_bid.bid.state

    def get_bid_count(self, donation_bid: DonationBid):
        return donation_bid.bid.count

    def get_bid_total(self, donation_bid: DonationBid):
        return donation_bid.bid.total

    def _has_permission(self, instance):
        return (
            any(
                f'tracker.{p}' in self.root_permissions
                for p in ('change_bid', 'view_bid')
            )
            or instance.bid.state in Bid.PUBLIC_STATES
        )

    def to_representation(self, instance):
        # final check
        assert self._has_permission(
            instance
        ), f'tried to serialize a hidden donation bid without permission {self.root_permissions}'
        return super().to_representation(instance)


class DonationSerializer(
    SerializerWithPermissionsMixin, EventNestedSerializerMixin, TrackerModelSerializer
):
    type = ClassNameField()
    donor_name = serializers.SerializerMethodField()
    bids = DonationBidSerializer(many=True, read_only=True)
    groups = AbstractTagField(
        model=DonationGroup, many=True, required=False, allow_create=True
    )

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
            'groups',
        )

    def __init__(
        self,
        *args,
        with_mod_comments=False,
        with_all_comments=False,
        with_donor_ids=False,
        with_groups=False,
        **kwargs,
    ):
        self.with_mod_comments = with_mod_comments
        self.with_all_comments = with_all_comments
        self.with_donor_ids = with_donor_ids
        self.with_groups = with_groups
        super().__init__(*args, **kwargs)

    def _has_permission(self, permission):
        return permission in self.permissions

    def get_donor_name(self, donation: Donation):
        if donation.anonymous():
            return Donor.ANONYMOUS
        if not donation.requestedalias:
            return Donor.ANONYMOUS

        return donation.requestedalias

    def to_representation(self, instance):
        assert not self.with_donor_ids or self._has_permission(
            'tracker.view_donor'
        ), 'attempting to serialize a donation with donor information without the expected permission'
        assert not self.with_mod_comments or self._has_permission(
            'tracker.view_donation'
        ), 'attempting to serialize a donation with moderator comment without the expected permission'
        assert not self.with_all_comments or self._has_permission(
            'tracker.view_comments'
        ), 'attempting to serialize a donation with all comments without the expected permission'
        assert not self.with_groups or self._has_permission(
            'tracker.view_donation'
        ), 'attempting to serialize a donation with groups without the expected permission'
        value = super().to_representation(instance)
        if not self.with_donor_ids:
            value.pop('donor', None)
        if not self.with_mod_comments:
            value.pop('modcomment', None)
        if not self.with_all_comments and instance.commentstate != 'APPROVED':
            value.pop('comment', None)
        if not self.with_groups:
            value.pop('groups')
        return value


class EventSerializer(PrimaryOrNaturalKeyLookup, TrackerModelSerializer):
    type = ClassNameField()
    # include these later
    # allowed_prize_countries = CountrySerializer(many=True)
    # disallowed_prize_regions = CountryRegionSerializer(many=True)
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
            'receivername',
            'receiver_short',
            'receiver_solicitation_text',
            'receiver_logo',
            'receiver_privacy_policy',
            'use_one_step_screening',
            'locked',
            'allow_donations',
            # 'allowed_prize_countries',
            # 'disallowed_prize_regions',
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


class SpeedRunSerializer(
    PrimaryOrNaturalKeyLookup,
    SerializerWithPermissionsMixin,
    EventNestedSerializerMixin,
    TrackerModelSerializer,
):
    type = ClassNameField()
    event = EventSerializer()
    runners = TalentSerializer(many=True, allow_empty=False)
    hosts = TalentSerializer(many=True, required=False)
    commentators = TalentSerializer(many=True, required=False)
    video_links = VideoLinkSerializer(many=True, required=False)
    priority_tag = AbstractTagField(
        model=Tag, allow_null=True, required=False, allow_create=True
    )
    tags = AbstractTagField(model=Tag, many=True, required=False, allow_create=True)

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
            'layout',
            'video_links',
            'priority_tag',
            'tags',
        )
        nested_creates = ('video_links',)
        extra_kwargs = {
            # TODO: almost assuredly a bug in DRF, see: https://github.com/encode/django-rest-framework/discussions/9538
            'order': {'default': None, 'required': False}
        }
        exclude_from_nested = ('event',)

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
        } & set(self.root_permissions)

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
    tags = AbstractTagField(model=Tag, many=True, required=False, allow_create=True)
    anchor = PrimaryKeyRelatedField(queryset=SpeedRun.objects.all(), required=False)

    class Meta:
        fields = (
            'type',
            'id',
            'event',
            'anchor',
            'order',
            'suborder',
            'length',
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
                value['suborder'] = 1

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
    interviewers = TalentSerializer(many=True, allow_empty=False)
    subjects = TalentSerializer(many=True, required=False)

    class Meta:
        model = Interview
        fields = InterstitialSerializer.Meta.fields + (
            'social_media',
            'interviewers',
            'topic',
            'public',
            'prerecorded',
            'producer',
            'subjects',
            'camera_operator',
        )


class MilestoneSerializer(
    SerializerWithPermissionsMixin, EventNestedSerializerMixin, TrackerModelSerializer
):
    type = ClassNameField()
    event = EventSerializer()
    run = PrimaryKeyRelatedField(queryset=SpeedRun.objects.all(), required=False)

    class Meta:
        model = Milestone
        fields = (
            'type',
            'id',
            'event',
            'start',
            'amount',
            'name',
            'run',
            'visible',
            'description',
            'short_description',
        )


class DonorSerializer(EventNestedSerializerMixin, TrackerModelSerializer):
    type = ClassNameField()
    alias = serializers.SerializerMethodField()
    totals = serializers.SerializerMethodField()

    def __init__(self, *args, include_totals=False, **kwargs):
        self.include_totals = include_totals
        super().__init__(*args, **kwargs)

    class Meta:
        model = Donor
        fields = (
            'type',
            'id',
            'alias',
            'totals',
        )

    def get_fields(self):
        fields = super().get_fields()
        if not self.include_totals:
            fields.pop('totals', None)
        return fields

    def get_alias(self, instance):
        return instance.full_alias

    def get_totals(self, instance):
        return sorted(
            (
                {
                    'event': c.event_id,
                    'total': c.donation_total,
                    'count': c.donation_count,
                    'avg': c.donation_avg,
                    'max': c.donation_max,
                }
                for c in instance.cache.all()
                if self.event_pk is None
                or c.event_id == self.event_pk
                or c.event_id is None
            ),
            key=lambda c: c['event'] or -1,
        )

    def to_representation(self, instance):
        value = super().to_representation(instance)
        if instance.visibility == 'ANON':
            value.pop('alias', None)
        return value


class PrizeSerializer(
    SerializerWithPermissionsMixin, EventNestedSerializerMixin, TrackerModelSerializer
):
    type = ClassNameField()
    event = EventSerializer()
    # TODO: when I figure out a better way to be selective about nested fields
    # startrun = SpeedRunSerializer()
    # endrun = SpeedRunSerializer()

    class Meta:
        model = Prize
        fields = (
            'type',
            'id',
            'event',
            'name',
            'state',
            'startrun',
            'endrun',
            'starttime',
            'endtime',
            'start_draw_time',
            'end_draw_time',
            'description',
            'shortdescription',
            'image',
            'altimage',
            'imagefile',
            'estimatedvalue',
            'minimumbid',
            'sumdonations',
            'provider',
            'creator',
            # 'creatoremail', TODO, maybe a privacy filter? how often does this get used?
            'creatorwebsite',
        )

    def validate(self, data):
        # TODO: allow assigning other handlers, but figure out what those permissions need to look like first
        if (
            'request' in self.context
            and 'view' in self.context
            and self.context['view'].action == 'create'
        ):
            data['handler'] = self.context['request'].user
        return super().validate(data)
