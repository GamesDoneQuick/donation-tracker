import enum
from contextlib import contextmanager

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from tracker import logutil
from tracker.analytics import AnalyticsEventTypes, analytics
from tracker.api.permissions import tracker_permission
from tracker.api.serializers import DonationSerializer
from tracker.consumers.processing import broadcast_processing_action
from tracker.models import Donation

CanChangeDonation = tracker_permission('tracker.change_donation')
CanSendToReader = tracker_permission('tracker.send_to_reader')
CanViewComments = tracker_permission('tracker.view_comments')


class DonationProcessingActionTypes(str, enum.Enum):
    UNPROCESSED = 'unprocessed'
    APPROVED = 'approved'
    DENIED = 'denied'
    FLAGGED = 'flagged'
    SENT_TO_READER = 'sent_to_reader'
    PINNED = 'pinned'
    UNPINNED = 'unpinned'


DONATION_CHANGE_LOG_MESSAGES = {
    DonationProcessingActionTypes.UNPROCESSED: 'reset donation comment processing status',
    DonationProcessingActionTypes.APPROVED: 'approved donation comment',
    DonationProcessingActionTypes.DENIED: 'denied donation comment',
    DonationProcessingActionTypes.FLAGGED: 'flagged donation to head',
    DonationProcessingActionTypes.SENT_TO_READER: 'sent donation to reader',
    DonationProcessingActionTypes.PINNED: 'pinned donation for reading',
    DonationProcessingActionTypes.UNPINNED: 'unpinned donation for reading',
}

DONATION_ACTION_ANALYTICS_EVENTS = {
    DonationProcessingActionTypes.UNPROCESSED: AnalyticsEventTypes.DONATION_COMMENT_UNPROCESSED,
    DonationProcessingActionTypes.APPROVED: AnalyticsEventTypes.DONATION_COMMENT_APPROVED,
    DonationProcessingActionTypes.DENIED: AnalyticsEventTypes.DONATION_COMMENT_DENIED,
    DonationProcessingActionTypes.FLAGGED: AnalyticsEventTypes.DONATION_COMMENT_FLAGGED,
    DonationProcessingActionTypes.SENT_TO_READER: AnalyticsEventTypes.DONATION_COMMENT_SENT_TO_READER,
    DonationProcessingActionTypes.PINNED: AnalyticsEventTypes.DONATION_COMMENT_PINNED,
    DonationProcessingActionTypes.UNPINNED: AnalyticsEventTypes.DONATION_COMMENT_UNPINNED,
}


def _get_donation_analytics_fields(donation: Donation):
    return {
        'event_id': donation.event.id,
        'donation_id': donation.id,
        'amount': donation.amount,
        'is_anonymous': donation.anonymous(),
        'num_bids': donation.bids.count(),
        'currency': donation.currency,
        'comment': donation.comment,
        'comment_language': donation.commentlanguage,
        'domain': donation.domain,
        # TODO: Update to track these fields properly
        'is_first_donation': False,
        'from_partner': False,
    }


def _track_donation_processing_event(
    action: DonationProcessingActionTypes,
    donation: Donation,
    request,
):
    # Add to local event audit log
    logutil.change(request, donation, DONATION_CHANGE_LOG_MESSAGES[action])

    # Track event to analytics database
    analytics.track(
        DONATION_ACTION_ANALYTICS_EVENTS[action],
        {
            **_get_donation_analytics_fields(donation),
            'user_id': request.user.pk,
        },
    )

    # Announce the action to all other processors
    broadcast_processing_action(request.user, donation, action)


class DonationChangeManager:
    def __init__(self, request, pk: str):
        self.request = request
        self.pk = pk

    @contextmanager
    def change_donation(self, action: DonationProcessingActionTypes):
        self.donation = get_object_or_404(Donation, pk=self.pk)
        yield self.donation
        self.donation.save()
        _track_donation_processing_event(
            action=action, request=self.request, donation=self.donation
        )

    def response(self):
        serializer = DonationSerializer(self.donation).data
        return Response(serializer)


class DonationViewSet(viewsets.GenericViewSet):
    serializer_class = DonationSerializer

    def get_queryset(self):
        """
        Processing only occurs on Donations that have settled their transaction
        and were not tests.
        """
        event_id = self.request.query_params.get('event_id')
        query = (
            Donation.objects.all()
            .filter(event_id=event_id, transactionstate='COMPLETED', testdonation=False)
            .order_by('timereceived')
        )

        after = self.request.query_params.get('after')
        if after is not None:
            query = query.filter(Q(timereceived__gte=after))

        return query

    @action(detail=False, methods=['get'], permission_classes=[CanViewComments])
    def unprocessed(self, _request):
        """
        Return a list of the oldest completed donations for the event which have
        not yet been processed in any way (e.g., are still PENDING for comment
        moderation), up to a maximum of 200 donations.
        """
        donations = (
            self.get_queryset()
            .filter(Q(commentstate='PENDING') | Q(readstate='PENDING'))
            .prefetch_related('bids')
        )[0:200]
        serializer = DonationSerializer(donations, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[CanViewComments])
    def flagged(self, _request):
        """
        Return a list of the oldest completed donations for the event which have
        been flagged for head review (e.g., are FLAGGED for read moderation),
        up to a maximum of 200 donations.
        """
        donations = (
            self.get_queryset()
            .filter(Q(commentstate='APPROVED') & Q(readstate='FLAGGED'))
            .prefetch_related('bids')
        )[0:200]
        serializer = DonationSerializer(donations, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[CanChangeDonation])
    def unprocess(self, request, pk):
        """
        Reset the comment and read states for the donation.
        """
        manager = DonationChangeManager(request, pk)
        with manager.change_donation(
            action=DonationProcessingActionTypes.UNPROCESSED
        ) as donation:
            donation.commentstate = 'PENDING'
            donation.readstate = 'PENDING'

        return manager.response()

    @action(detail=True, methods=['post'], permission_classes=[CanChangeDonation])
    def approve_comment(self, request, pk):
        """
        Mark the comment for the donation as approved, but do not send it on to
        be read.
        """
        manager = DonationChangeManager(request, pk)
        with manager.change_donation(
            action=DonationProcessingActionTypes.APPROVED
        ) as donation:
            donation.commentstate = 'APPROVED'
            donation.readstate = 'IGNORED'

        return manager.response()

    @action(detail=True, methods=['post'], permission_classes=[CanChangeDonation])
    def deny_comment(self, request, pk):
        """
        Mark the comment for the donation as explicitly denied and ignored.
        """
        manager = DonationChangeManager(request, pk)
        with manager.change_donation(
            action=DonationProcessingActionTypes.DENIED
        ) as donation:
            donation.commentstate = 'DENIED'
            donation.readstate = 'IGNORED'

        return manager.response()

    @action(detail=True, methods=['post'], permission_classes=[CanChangeDonation])
    def flag(self, request, pk):
        """
        Mark the donation as approved, but flagged for head donations to review
        before sending to the reader. This should only be called when the event
        is using two step screening.
        """
        manager = DonationChangeManager(request, pk)
        with manager.change_donation(
            action=DonationProcessingActionTypes.FLAGGED
        ) as donation:
            donation.commentstate = 'APPROVED'
            donation.readstate = 'FLAGGED'

        return manager.response()

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[CanChangeDonation & CanSendToReader],
    )
    def send_to_reader(self, request, pk):
        """
        Mark the donation as approved and send it directly to the reader.
        """
        manager = DonationChangeManager(request, pk)
        with manager.change_donation(
            action=DonationProcessingActionTypes.SENT_TO_READER
        ) as donation:
            donation.commentstate = 'APPROVED'
            donation.readstate = 'READY'

        return manager.response()

    @action(detail=True, methods=['post'], permission_classes=[CanChangeDonation])
    def pin(self, request, pk):
        """
        Mark the donation as pinned to the top of the reader's view.
        """
        manager = DonationChangeManager(request, pk)
        with manager.change_donation(
            action=DonationProcessingActionTypes.PINNED
        ) as donation:
            donation.pinned = True

        return manager.response()

    @action(detail=True, methods=['post'], permission_classes=[CanChangeDonation])
    def unpin(self, request, pk):
        """
        Umark the donation as pinned, returning it to a normal position in the donation list.
        """
        manager = DonationChangeManager(request, pk)
        with manager.change_donation(
            action=DonationProcessingActionTypes.UNPINNED
        ) as donation:
            donation.pinned = False

        return manager.response()
