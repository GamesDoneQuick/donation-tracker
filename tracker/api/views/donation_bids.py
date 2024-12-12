from django.db.models import Q

from tracker import models
from tracker.api.pagination import TrackerPagination
from tracker.api.permissions import DonationBidStatePermission
from tracker.api.serializers import DonationBidSerializer
from tracker.api.views import TrackerReadViewSet, WithSerializerPermissionsMixin


class DonationBidViewSet(WithSerializerPermissionsMixin, TrackerReadViewSet):
    serializer_class = DonationBidSerializer
    pagination_class = TrackerPagination
    permission_classes = [DonationBidStatePermission]
    queryset = models.DonationBid.objects.select_related('bid')

    def __init__(self, *args, donation=None, bid=None, **kwargs):
        self.donation = donation
        self.bid = bid
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        # this can be filtered in multiple ways
        # - by donation, which excludes hidden children unless explicitly asked for
        # - by exact bid, which includes the descendant tree if there is one, excluding
        #   hidden descendants unless explicitly asked for, or if the parent itself is hidden
        # note that we NEVER return bids attached to pending donations from this endpoint, if
        #  you really need that, you can look at the admin page
        queryset = queryset.filter(donation__transactionstate='COMPLETED')
        assert self.donation or self.bid, 'did not get either donation or bid'
        state_filter = Q()
        if 'all' not in self.request.query_params:
            state_filter = Q(bid__state__in=models.Bid.PUBLIC_STATES)
        if self.donation:
            queryset = queryset.filter(Q(donation=self.donation) & state_filter)
        if self.bid:
            if self.bid.state not in models.Bid.PUBLIC_STATES:
                # if we're requesting a specific bid that's not public, just assume we want to view all states,
                #  since we would have gotten a 404 by now if we didn't already have permission
                state_filter = Q()
            queryset = queryset.filter(
                (Q(bid=self.bid) | Q(bid__in=self.bid.get_descendants()) & state_filter)
            )
        return queryset
