import logging

from django.utils.translation import gettext_lazy as _
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from tracker.api.filters import BidFilter
from tracker.api.pagination import TrackerPagination
from tracker.api.permissions import (
    BidFeedPermission,
    BidStatePermission,
    EventLockedPermission,
)
from tracker.api.serializers import BidSerializer
from tracker.api.views import (
    EventNestedMixin,
    TrackerReadViewSet,
    TrackerUpdateMixin,
    WithPermissionsMixin,
)
from tracker.models import Bid, SpeedRun

logger = logging.getLogger(__name__)


class BidViewSet(
    WithPermissionsMixin,
    EventNestedMixin,
    mixins.CreateModelMixin,
    TrackerUpdateMixin,
    TrackerReadViewSet,
):
    queryset = Bid.objects.all()
    serializer_class = BidSerializer
    pagination_class = TrackerPagination
    permission_classes = [EventLockedPermission, BidFeedPermission, BidStatePermission]
    filter_backends = [BidFilter]

    def _include_hidden(self, instance=None):
        # include hidden bids if we're asking for one hidden bid, or if we're asking for one of the hidden feeds
        return (
            isinstance(instance, Bid) and instance.state not in ['OPENED', 'CLOSED']
        ) or self.get_feed() in ('pending', 'all')

    def get_feed(self):
        return self.kwargs.get('feed', None)

    def get_event_from_request(self, request):
        event = super().get_event_from_request(request)
        if event:
            return event
        if 'speedrun' in request.data:
            try:
                speedrun = SpeedRun.objects.filter(pk=request.data['speedrun']).first()
                return speedrun and speedrun.event
            except ValueError:
                pass
        if 'parent' in request.data:
            try:
                bid = Bid.objects.filter(pk=request.data['parent']).first()
                return bid and bid.event
            except ValueError:
                pass
        return None

    def get_serializer(self, instance=None, *args, **kwargs):
        return super().get_serializer(
            instance,
            *args,
            include_hidden=self._include_hidden(instance),
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
