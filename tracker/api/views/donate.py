from __future__ import annotations

import contextlib
import logging
import secrets
import time
from collections import defaultdict
from decimal import Decimal
from functools import reduce

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.signing import BadSignature, TimestampSigner
from django.db import transaction
from django.http import HttpResponse
from django.template.response import SimpleTemplateResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from paypal.standard.forms import PayPalPaymentsForm
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ErrorDetail, PermissionDenied, ValidationError
from rest_framework.fields import (
    BooleanField,
    CharField,
    DecimalField,
    EmailField,
    IntegerField,
)
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.serializers import Serializer, as_serializer_error
from rest_framework.viewsets import GenericViewSet

from tracker import settings
from tracker.api.serializers import DonationSerializer, EnsureSerializableMixin
from tracker.compat import pairwise, reverse
from tracker.models import Bid, Donation, Event
from tracker.models.donation import Donor

logger = logging.getLogger(__file__)


def _trim(d: float | int):
    return Decimal(d).quantize(Decimal('0.00'))


class NewDonationBidSerializer(EnsureSerializableMixin, Serializer):
    id = IntegerField(required=False)
    parent = IntegerField(required=False)
    name = CharField(required=False)
    amount = DecimalField(
        max_digits=20,
        decimal_places=2,
        coerce_to_string=False,
        max_value=Decimal(100000),
        min_value=Decimal(1),
    )

    def to_internal_value(self, data):
        if isinstance(data.get('amount'), float):
            data['amount'] = _trim(data['amount'])
        return super().to_internal_value(data)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        errors = defaultdict(list)

        attrs['amount'] = _trim(attrs['amount'])

        if 'id' in attrs:
            bid = Bid.objects.public().filter(id=attrs['id']).first()
            if bid is None:
                errors['id'].append(
                    ErrorDetail(
                        'Specified bid either does not exist or is not public.',
                        code='invalid',
                    )
                )
            else:
                if not bid.istarget:
                    errors['id'].append(
                        ErrorDetail(
                            'Specified bid is not a valid target.', code='invalid'
                        )
                    )
                if bid.state != 'OPENED':
                    errors['id'].append(
                        ErrorDetail(
                            'Specified bid is not currently open.', code='invalid'
                        )
                    )
            if 'parent' in attrs:
                errors['id'].append(
                    ErrorDetail(
                        'Cannot specify both `parent` and `id`.', code='invalid'
                    )
                )
                errors['parent'].append(
                    ErrorDetail(
                        'Cannot specify both `parent` and `id`.', code='invalid'
                    )
                )
            elif 'name' in attrs:
                errors['id'].append(
                    ErrorDetail('Cannot specify both `name` and `id`.', code='invalid')
                )
                errors['name'].append(
                    ErrorDetail('Cannot specify both `name` and `id`.', code='invalid')
                )
        elif 'parent' in attrs:
            name = attrs.get('name', '')
            if name == '':
                errors['name'].append(
                    ErrorDetail('Must specify `name` with `parent`.', code='invalid')
                )
            bid = Bid.objects.public().filter(id=attrs['parent']).first()
            if bid is None:
                errors['parent'].append(
                    ErrorDetail(
                        'Specified bid either does not exist or is not public.',
                        code='invalid',
                    )
                )
            else:
                if not bid.allowuseroptions:
                    errors['parent'].append(
                        ErrorDetail(
                            'Specified bid does not accept new suggestions.',
                            code='invalid',
                        )
                    )
                if bid.state != 'OPENED':
                    errors['parent'].append(
                        ErrorDetail(
                            'Specified bid is not currently open.', code='invalid'
                        )
                    )
                if (
                    bid.option_max_length is not None
                    and len(name) > bid.option_max_length
                ):
                    errors['name'].append(
                        ErrorDetail(
                            f'Specified name is too long. Maximum length is {bid.option_max_length}.',
                            code='invalid',
                        )
                    )

        if errors:
            raise ValidationError(errors)

        return attrs

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if ret.get('id', None) is None:
            ret.pop('id', None)
        else:
            ret.pop('parent', None)
            ret.pop('name', None)
        return ret


class NewDonationSerializer(EnsureSerializableMixin, Serializer):
    amount = DecimalField(
        max_digits=20,
        decimal_places=2,
        coerce_to_string=False,
    )
    bids = NewDonationBidSerializer(many=True)
    comment = CharField(allow_blank=True, max_length=5000)
    domain = CharField(required=False)
    domainId = CharField(read_only=True)
    donor_id = IntegerField(required=False)
    donor_email = EmailField(required=False)
    email_optin = BooleanField()
    event = IntegerField()
    requested_alias = CharField(
        allow_blank=True,
        max_length=Donation._meta.get_field('requestedalias').max_length,
    )
    requested_email = EmailField(
        allow_blank=True,
        max_length=Donation._meta.get_field('requestedemail').max_length,
    )

    def to_internal_value(self, data):
        if isinstance(data.get('amount'), float):
            data['amount'] = _trim(data['amount'])
        return super().to_internal_value(data)

    def validate(self, attrs):
        errors = defaultdict(list)

        attrs['amount'] = _trim(attrs['amount'])

        event = Event.objects.filter(id=attrs['event']).first()
        if event is None:
            errors['event'].append(
                ErrorDetail(
                    'Specified event does not exist or is not public.', code='invalid'
                )
            )
        else:
            if not event.allow_donations:
                errors['event'].append(
                    ErrorDetail(
                        'Specified event is not currently accepting donations.',
                        code='invalid',
                    )
                )
            if attrs['amount'] < event.minimumdonation:
                errors['amount'].append(
                    ErrorDetail(
                        'Donation amount is below event minimum.', code='invalid'
                    )
                )
            elif attrs['amount'] > (
                event.maximum_paypal_donation or settings.TRACKER_PAYPAL_MAXIMUM_AMOUNT
            ):
                errors['amount'].append(
                    ErrorDetail(
                        'Donation amount is above event maximum.', code='invalid'
                    )
                )
            for bid in attrs['bids']:
                with contextlib.suppress(TypeError, ValueError):
                    if 'id' in bid:
                        bid = Bid.objects.filter(id=bid['id']).first()
                    elif 'parent' in bid:
                        bid = Bid.objects.filter(id=bid['parent']).first()
                    else:
                        continue
                    if bid.event != event:
                        errors['bids'].append(
                            ErrorDetail(
                                'Specified bid does not belong to this event.',
                                code='invalid',
                            )
                        )
            for a, b in pairwise(
                sorted(
                    attrs['bids'],
                    key=lambda b: (
                        b.get('id', -1),
                        b.get('parent', -1),
                        b.get('name', ''),
                    ),
                )
            ):
                if ('id' in a and a['id'] == b.get('id', None)) or (
                    'parent' in a
                    and 'name' in a
                    and a['parent'] == b.get('parent', None)
                    and a['name'] == b.get('name', None)
                ):
                    errors['bids'].append(
                        ErrorDetail(
                            'Duplicate assignment.',
                            code='invalid',
                        )
                    )

        domain = attrs.get('domain', 'LOCAL')

        if domain == 'LOCAL':
            if 'donor_id' in attrs:
                if not Donor.objects.filter(id=attrs['donor_id']).exists():
                    errors['donor_id'].append(
                        ErrorDetail('Specified donor does not exist.', code='invalid')
                    )
            elif 'donor_email' in attrs:
                if not Donor.objects.filter(
                    email__iexact=attrs['donor_email']
                ).exists():
                    errors['donor_email'].append(
                        ErrorDetail(
                            'Specified donor email could not be found.', code='invalid'
                        )
                    )
            else:
                errors['domain'].append(
                    ErrorDetail(
                        'Local donations require either `donor_id` or `donor_email` field.',
                        code='invalid',
                    )
                )
        elif domain == 'PAYPAL':
            pass
        else:
            errors['domain'].append(
                ErrorDetail(
                    'This endpoint does not support creation of Donations with that domain.',
                    code='invalid',
                )
            )

        bid_total = reduce(lambda a, b: a + b, (b['amount'] for b in attrs['bids']), 0)
        if bid_total > attrs['amount']:
            errors['amount'].append(
                ErrorDetail('Allocated bids exceeds amount.', code='invalid')
            )

        if errors:
            raise ValidationError(errors)

        attrs['domainId'] = f'{int(time.time())}-{secrets.token_hex(16)}'

        return attrs


class DonateViewSet(GenericViewSet):
    serializer_class = NewDonationSerializer

    def get_queryset(self):
        return None

    @method_decorator(csrf_protect)
    def list(self, request, *args, **kwargs):
        return HttpResponse(status=204)

    @transaction.atomic
    def _create_donation(self, serializer):
        try:
            data = serializer.data
            event = Event.objects.get(id=data['event'])
            query = dict(
                event=event,
                domain='PAYPAL',
                domainId=data['domainId'],
                currency=event.paypalcurrency,
                amount=_trim(data['amount']),
                comment=data['comment'],
                requestedalias=data['requested_alias'],
                requestedemail=data['requested_email'],
                requestedsolicitemail='OPTIN' if data['email_optin'] else 'OPTOUT',
                requestedvisibility='ALIAS' if data['requested_alias'] else 'ANON',
            )
            # guard against accidental short-term replays (e.g. hitting the Back button)
            donation = Donation.objects.filter(**query).first()
            if donation is None:
                donation = Donation(**query)
                donation.full_clean()
                donation.save()
                # get_or_create isn't usable in transactions, so for new suggestions we lock the parents instead to assure atomicity
                Bid.objects.filter(
                    id__in=(b['parent'] for b in data['bids'] if 'parent' in b)
                ).select_for_update()
                for bid_data in data['bids']:
                    if 'id' in bid_data:
                        bid = Bid.objects.get(id=bid_data['id'])
                    else:
                        try:
                            bid = Bid.objects.get(
                                parent_id=bid_data['parent'],
                                name__iexact=bid_data['name'],
                            )
                        except Bid.DoesNotExist:
                            bid = Bid.objects.create(
                                parent_id=bid_data['parent'],
                                name=bid_data['name'],
                                state='PENDING',
                                istarget=True,
                            )
                            bid.full_clean()
                    donation.bids.create(
                        bid=bid,
                        amount=_trim(bid_data['amount']),
                    )
                donation.full_clean()
                donation.refresh_from_db()  # ensure all values are as they'd be when fetched fresh
            return donation
        except ObjectDoesNotExist:
            # this could theoretically happen if an object is deleted between the time the signed payload is generated and when it is processed
            raise ValidationError('Invalid payload.')

    # disable CSRF since the query parameter is already signed from before
    @action(
        url_name='paypal-confirm',
        detail=False,
        methods=['post'],
        authentication_classes=[],
        renderer_classes=[JSONRenderer],
    )
    def paypal_confirm(self, request, *args, **kwargs):
        try:
            timed_signer = TimestampSigner(salt=request.META['REMOTE_ADDR'])
            try:
                signed = timed_signer.unsign_object(
                    request.query_params.get('q', ''),
                    max_age=settings.TRACKER_PAYPAL_MAX_DONATE_AGE,
                )
            except BadSignature as exc:
                logger.warning('Bad signature.', exc_info=exc)
                raise ValidationError('Invalid payload.')
            serializer = self.get_serializer(data=signed)
            serializer.is_valid(raise_exception=True)
            donation = self._create_donation(serializer)
            donation.refresh_from_db()
            custom = donation.paypal_signature
            # if this ever happens there were some very bad assumptions made
            assert len(custom) < 256, 'custom field too long, report this as a bug'
            paypal_dict = {
                'amount': str(donation.amount),
                'cmd': '_donations',
                'business': donation.event.paypalemail,
                'image_url': donation.event.paypalimgurl,
                'item_name': donation.event.receivername,
                'notify_url': request.build_absolute_uri(reverse('tracker:paypal-ipn')),
                'return': request.build_absolute_uri(reverse('tracker:paypal_return')),
                'cancel_return': request.build_absolute_uri(
                    reverse('tracker:paypal_cancel')
                ),
                'custom': custom,
                'currency_code': donation.event.paypalcurrency,
                'no_shipping': 0,
            }
            form = PayPalPaymentsForm(button_type='donate', initial=paypal_dict)

            return SimpleTemplateResponse(
                'tracker/paypal_redirect.html',
                context={'event': donation.event, 'form': form},
            )
        except DjangoValidationError as exc:
            return self.get_exception_handler()(
                ValidationError(detail=as_serializer_error(exc)),
                self.get_exception_handler_context(),
            )
        except ValidationError as exc:
            return self.get_exception_handler()(
                exc, self.get_exception_handler_context()
            )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.data['domain'] == 'PAYPAL':
            signer = TimestampSigner(salt=request.META['REMOTE_ADDR'])
            data = signer.sign_object(serializer.data, compress=True)
            return Response(
                {
                    'confirm_url': request.build_absolute_uri(
                        reverse(
                            'tracker:api_v2:donate-paypal-confirm', query={'q': data}
                        )
                    )
                },
                status=status.HTTP_201_CREATED,
            )
        else:
            if not request.user.has_perm('tracker.add_donation'):
                raise PermissionDenied
            donation = self._create_donation(serializer)
            return Response(
                DonationSerializer(donation).data,
                status=status.HTTP_201_CREATED,
            )
