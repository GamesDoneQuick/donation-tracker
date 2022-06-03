from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from tracker import logutil
from tracker.analytics import analytics, AnalyticsEventTypes
from tracker.api.permissions import tracker_permission
from tracker.api.serializers import DonationSerializer
from tracker.models import Donation

CanChangeDonation = tracker_permission('tracker.change_donation')
CanSendToReader = tracker_permission('tracker.send_to_reader')
CanViewComments = tracker_permission('tracker.view_comments')


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
    type: AnalyticsEventTypes, label: str, donation: Donation, request,
):
    analytics.track(
        type, {**_get_donation_analytics_fields(donation), 'user_id': request.user.pk,},
    )
    logutil.change(request, donation, label)


class DonationViewSet(viewsets.GenericViewSet):
    serializer_class = DonationSerializer

    def get_queryset(self):
        """
        Processing only occurs on Donations that have settled their transaction
        and were not tests.
        """
        event_id = self.request.query_params.get('event_id')
        return (
            Donation.objects.all()
            .filter(event_id=event_id, transactionstate='COMPLETED', testdonation=False)
            .order_by('timereceived')
        )

    @action(detail=False, methods=['get'], permission_classes=[CanViewComments])
    def unprocessed(self, _request):
        donations = (
            self.get_queryset()
            .filter((Q(commentstate='PENDING') | Q(readstate='PENDING')))
            .prefetch_related('bids')
        )
        paginator = Paginator(donations, 50)
        serializer = DonationSerializer(paginator.get_page(1), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[CanChangeDonation])
    def unprocess(self, request, pk=None):
        """
        Reset the comment and read states for the donation.
        """
        donation = get_object_or_404(Donation, pk=pk)
        donation.commentstate = 'PENDING'
        donation.readstate = 'PENDING'
        donation.save()

        _track_donation_processing_event(
            type=AnalyticsEventTypes.DONATION_COMMENT_UNPROCESSED,
            label='reset donation comment processing status',
            request=request,
            donation=donation,
        )

        serializer = DonationSerializer(donation)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[CanChangeDonation])
    def approve_comment(self, request, pk=None):
        """
        Mark the comment for the donation as approved, but do not send it on to
        be read.
        """
        donation = get_object_or_404(Donation, pk=pk)
        donation.commentstate = 'APPROVED'
        donation.readstate = 'IGNORED'
        donation.save()

        _track_donation_processing_event(
            type=AnalyticsEventTypes.DONATION_COMMENT_APPROVED,
            label='approved donation comment',
            request=request,
            donation=donation,
        )

        serializer = DonationSerializer(donation)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[CanChangeDonation])
    def deny_comment(self, request, pk=None):
        """
        Mark the comment for the donation as explicitly denied and ignored.
        """
        donation = get_object_or_404(Donation, pk=pk)
        donation.commentstate = 'DENIED'
        donation.readstate = 'IGNORED'
        donation.save()

        _track_donation_processing_event(
            type=AnalyticsEventTypes.DONATION_COMMENT_DENIED,
            label='denied donation comment',
            request=request,
            donation=donation,
        )

        serializer = DonationSerializer(donation)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[CanChangeDonation])
    def flag(self, request, pk=None):
        """
        Mark the donation as approved, but flagged for head donations to review
        before sending to the reader. This should only be called when the event
        is using two step screening.
        """
        donation = get_object_or_404(Donation, pk=pk)
        donation.commentstate = 'APPROVED'
        donation.readstate = 'FLAGGED'
        donation.save()

        _track_donation_processing_event(
            type=AnalyticsEventTypes.DONATION_COMMENT_FLAGGED,
            label='flagged donation to head',
            request=request,
            donation=donation,
        )

        serializer = DonationSerializer(donation)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[CanChangeDonation, CanSendToReader],
    )
    def send_to_reader(self, request, pk=None):
        """
        Mark the donation as approved and send it directly to the reader.
        """
        donation = get_object_or_404(Donation, pk=pk)
        donation.commentstate = 'APPROVED'
        donation.readstate = 'READY'
        donation.save()

        _track_donation_processing_event(
            type=AnalyticsEventTypes.DONATION_COMMENT_SENT_TO_READER,
            label='sent donation to reader',
            request=request,
            donation=donation,
        )

        serializer = DonationSerializer(donation)
        return Response(serializer.data)
