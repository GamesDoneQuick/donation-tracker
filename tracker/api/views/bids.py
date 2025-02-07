import contextlib
import logging

from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import action
from rest_framework.exceptions import ErrorDetail, PermissionDenied, ValidationError
from rest_framework.response import Response

from tracker.api import messages
from tracker.api.filters import BidFilter
from tracker.api.pagination import TrackerPagination
from tracker.api.permissions import (
    BidApprovalPermission,
    BidFeedPermission,
    BidStatePermission,
)
from tracker.api.serializers import BidSerializer
from tracker.api.views import (
    EventNestedMixin,
    TrackerFullViewSet,
    WithSerializerPermissionsMixin,
)
from tracker.api.views.donation_bids import DonationBidViewSet
from tracker.models import Bid, SpeedRun

logger = logging.getLogger(__name__)


class BidViewSet(
    WithSerializerPermissionsMixin,
    EventNestedMixin,
    TrackerFullViewSet,
):
    queryset = Bid.objects.all()
    serializer_class = BidSerializer
    pagination_class = TrackerPagination
    permission_classes = [BidFeedPermission, BidStatePermission]
    filter_backends = [BidFilter]

    def _include_hidden(self, instance=None, data=None):
        # include hidden bids if we're asking for one hidden bid, or if we're asking for one of the hidden feeds
        return (
            (isinstance(instance, Bid) and instance.state not in Bid.PUBLIC_STATES)
            or self.get_feed() in ('pending', 'all')
            or (data and data.get('state', None) in Bid.HIDDEN_STATES)
            or 'include_hidden' in self.request.query_params
        )

    def get_feed(self):
        return self.kwargs.get('feed', None)

    def get_event_from_request(self):
        event = super().get_event_from_request()
        if event:
            return event
        if 'speedrun' in self.request.data:
            with contextlib.suppress(ValueError):
                speedrun = SpeedRun.objects.filter(
                    pk=self.request.data['speedrun']
                ).first()
                return speedrun and speedrun.event
        if 'parent' in self.request.data:
            with contextlib.suppress(ValueError):
                bid = Bid.objects.filter(pk=self.request.data['parent']).first()
                return bid and bid.event
        return None

    def get_serializer(self, instance=None, *args, **kwargs):
        return super().get_serializer(
            instance,
            *args,
            include_hidden=self._include_hidden(instance, kwargs.get('data', None)),
            feed=self.get_feed(),
            **kwargs,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, tree=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        if not (
            request.user.has_perm('tracker.top_level_bid') or 'parent' in request.data
        ):
            raise PermissionDenied(
                detail=_('You are not authorized to create new top level bids'),
                code='unauthorized_top_level',
            )
        return super().create(request, *args, **kwargs)

    @action(detail=False)
    def tree(self, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset().filter(level=0))
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, tree=True, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['get'])
    def donations(self, request, *args, **kwargs):
        viewset = DonationBidViewSet(request=request, bid=self.get_object())
        viewset.initial(request, *args, **kwargs)
        return viewset.list(request, *args, **kwargs)

    def _change_bid_state(self, state):
        bid = self.get_object()
        if bid.state != 'PENDING':
            raise ValidationError(
                {
                    'state': ErrorDetail(
                        messages.INVALID_BID_APPROVAL_STATE,
                        code=messages.INVALID_BID_APPROVAL_STATE_CODE,
                    )
                }
            )
        serializer = self.get_serializer(bid, data={'state': state}, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['patch'],
        permission_classes=[BidApprovalPermission],
        include_tracker_permissions=False,
    )
    def approve(self, *args, **kwargs):
        # note: this ends up taking the parent state, whatever that happens to be
        return self._change_bid_state('OPENED')

    @action(
        detail=True,
        methods=['patch'],
        permission_classes=[BidApprovalPermission],
        include_tracker_permissions=False,
    )
    def deny(self, *args, **kwargs):
        return self._change_bid_state('DENIED')
