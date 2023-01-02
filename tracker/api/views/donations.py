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
from tracker.models import Donation

CanChangeDonation = tracker_permission('tracker.change_donation')
CanSendToReader = tracker_permission('tracker.send_to_reader')
CanViewComments = tracker_permission('tracker.view_comments')

DONATION_CHANGE_LOG_MESSAGES = {
    'unprocessed': 'reset donation comment processing status',
    'approved': 'approved donation comment',
    'denied': 'denied donation comment',
    'flagged': 'flagged donation to head',
    'sent_to_reader': 'sent donation to reader',
    'pinned': 'pinned donation for reading',
    'unpinned': 'unpinned donation for reading',
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
    type: AnalyticsEventTypes,
    label: str,
    donation: Donation,
    request,
):
    analytics.track(
        type,
        {
            **_get_donation_analytics_fields(donation),
            'user_id': request.user.pk,
        },
    )
    logutil.change(request, donation, label)


class DonationChangeManager:
    def __init__(self, request, pk: str):
        self.request = request
        self.pk = pk

    @contextmanager
    def change_donation(self):
        self.donation = get_object_or_404(Donation, pk=self.pk)
        yield self.donation
        self.donation.save()

    def track(self, type: AnalyticsEventTypes, label: str):
        _track_donation_processing_event(
            type=type,
            label=label,
            request=self.request,
            donation=self.donation,
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
        moderation), up to a maximum of 50 donations.
        """
        donations = (
            self.get_queryset()
            .filter(Q(commentstate='PENDING') | Q(readstate='PENDING'))
            .prefetch_related('bids')
        )[0:50]
        serializer = DonationSerializer(donations, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[CanViewComments])
    def flagged(self, _request):
        """
        Return a list of the oldest completed donations for the event which have
        been flagged for head review (e.g., are FLAGGED for read moderation),
        up to a maximum of 50 donations.
        """
        donations = (
            self.get_queryset()
            .filter(Q(commentstate='APPROVED') & Q(readstate='FLAGGED'))
            .prefetch_related('bids')
        )[0:50]
        serializer = DonationSerializer(donations, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[CanChangeDonation])
    def unprocess(self, request, pk):
        """
        Reset the comment and read states for the donation.
        """
        manager = DonationChangeManager(request, pk)
        with manager.change_donation() as donation:
            donation.commentstate = 'PENDING'
            donation.readstate = 'PENDING'

        manager.track(
            type=AnalyticsEventTypes.DONATION_COMMENT_UNPROCESSED,
            label=DONATION_CHANGE_LOG_MESSAGES['unprocessed'],
        )
        return manager.response()

    @action(detail=True, methods=['post'], permission_classes=[CanChangeDonation])
    def approve_comment(self, request, pk):
        """
        Mark the comment for the donation as approved, but do not send it on to
        be read.
        """
        manager = DonationChangeManager(request, pk)
        with manager.change_donation() as donation:
            donation.commentstate = 'APPROVED'
            donation.readstate = 'IGNORED'

        manager.track(
            type=AnalyticsEventTypes.DONATION_COMMENT_APPROVED,
            label=DONATION_CHANGE_LOG_MESSAGES['approved'],
        )
        return manager.response()

    @action(detail=True, methods=['post'], permission_classes=[CanChangeDonation])
    def deny_comment(self, request, pk):
        """
        Mark the comment for the donation as explicitly denied and ignored.
        """
        manager = DonationChangeManager(request, pk)
        with manager.change_donation() as donation:
            donation.commentstate = 'DENIED'
            donation.readstate = 'IGNORED'

        manager.track(
            type=AnalyticsEventTypes.DONATION_COMMENT_DENIED,
            label=DONATION_CHANGE_LOG_MESSAGES['denied'],
        )
        return manager.response()

    @action(detail=True, methods=['post'], permission_classes=[CanChangeDonation])
    def flag(self, request, pk):
        """
        Mark the donation as approved, but flagged for head donations to review
        before sending to the reader. This should only be called when the event
        is using two step screening.
        """
        manager = DonationChangeManager(request, pk)
        with manager.change_donation() as donation:
            donation.commentstate = 'APPROVED'
            donation.readstate = 'FLAGGED'

        manager.track(
            type=AnalyticsEventTypes.DONATION_COMMENT_FLAGGED,
            label=DONATION_CHANGE_LOG_MESSAGES['flagged'],
        )
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
        with manager.change_donation() as donation:
            donation.commentstate = 'APPROVED'
            donation.readstate = 'READY'

        manager.track(
            type=AnalyticsEventTypes.DONATION_COMMENT_SENT_TO_READER,
            label=DONATION_CHANGE_LOG_MESSAGES['sent_to_reader'],
        )
        return manager.response()

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[CanChangeDonation],
    )
    def pin(self, request, pk):
        """
        Mark the donation as pinned to the top of the reader's view.
        """
        manager = DonationChangeManager(request, pk)
        with manager.change_donation() as donation:
            donation.pinned = True

        manager.track(
            type=AnalyticsEventTypes.DONATION_COMMENT_PINNED,
            label=DONATION_CHANGE_LOG_MESSAGES['pinned'],
        )
        return manager.response()

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[CanChangeDonation],
    )
    def unpin(self, request, pk):
        """
        Umark the donation as pinned, returning it to a normal position in the donation list.
        """
        manager = DonationChangeManager(request, pk)
        with manager.change_donation() as donation:
            donation.pinned = False

        manager.track(
            type=AnalyticsEventTypes.DONATION_COMMENT_UNPINNED,
            label=DONATION_CHANGE_LOG_MESSAGES['unpinned'],
        )
        return manager.response()
