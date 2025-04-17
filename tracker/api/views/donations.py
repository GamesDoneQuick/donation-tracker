import enum
from contextlib import contextmanager

from rest_framework.decorators import action
from rest_framework.exceptions import ErrorDetail, ValidationError
from rest_framework.response import Response

from tracker import logutil
from tracker.analytics import AnalyticsEventTypes, analytics
from tracker.api.filters import DonationFilter
from tracker.api.pagination import TrackerPagination
from tracker.api.permissions import (
    CanSendToReader,
    DonationQueryPermission,
    tracker_permission,
)
from tracker.api.serializers import DonationSerializer
from tracker.api.views import (
    EventNestedMixin,
    TrackerReadViewSet,
    WithSerializerPermissionsMixin,
)
from tracker.api.views.donation_bids import DonationBidViewSet
from tracker.consumers.processing import broadcast_donation_processing_action
from tracker.models import Donation, DonationGroup

CanViewComments = tracker_permission('tracker.view_comments')
CanViewDonations = tracker_permission('tracker.view_donation')


class DonationProcessingActionTypes(str, enum.Enum):
    UNPROCESSED = 'unprocessed'
    APPROVED = 'approved'
    DENIED = 'denied'
    FLAGGED = 'flagged'
    SENT_TO_READER = 'sent_to_reader'
    PINNED = 'pinned'
    UNPINNED = 'unpinned'
    READ = 'read'
    IGNORED = 'ignored'
    MOD_COMMENT_EDITED = 'mod_comment_edited'
    GROUPS_CHANGED = 'groups_changed'


DONATION_CHANGE_LOG_MESSAGES = {
    DonationProcessingActionTypes.UNPROCESSED: 'reset donation comment processing status',
    DonationProcessingActionTypes.APPROVED: 'approved donation comment',
    DonationProcessingActionTypes.DENIED: 'denied donation comment',
    DonationProcessingActionTypes.FLAGGED: 'flagged donation to head',
    DonationProcessingActionTypes.SENT_TO_READER: 'sent donation to reader',
    DonationProcessingActionTypes.PINNED: 'pinned donation for reading',
    DonationProcessingActionTypes.UNPINNED: 'unpinned donation for reading',
    DonationProcessingActionTypes.READ: 'read donation',
    DonationProcessingActionTypes.IGNORED: 'ignored donation',
    DonationProcessingActionTypes.MOD_COMMENT_EDITED: 'edited the mod comment',
    DonationProcessingActionTypes.GROUPS_CHANGED: 'changed groups',
}

DONATION_ACTION_ANALYTICS_EVENTS = {
    DonationProcessingActionTypes.UNPROCESSED: AnalyticsEventTypes.DONATION_COMMENT_UNPROCESSED,
    DonationProcessingActionTypes.APPROVED: AnalyticsEventTypes.DONATION_COMMENT_APPROVED,
    DonationProcessingActionTypes.DENIED: AnalyticsEventTypes.DONATION_COMMENT_DENIED,
    DonationProcessingActionTypes.FLAGGED: AnalyticsEventTypes.DONATION_COMMENT_FLAGGED,
    DonationProcessingActionTypes.SENT_TO_READER: AnalyticsEventTypes.DONATION_COMMENT_SENT_TO_READER,
    DonationProcessingActionTypes.PINNED: AnalyticsEventTypes.DONATION_COMMENT_PINNED,
    DonationProcessingActionTypes.UNPINNED: AnalyticsEventTypes.DONATION_COMMENT_UNPINNED,
    DonationProcessingActionTypes.READ: AnalyticsEventTypes.DONATION_COMMENT_READ,
    DonationProcessingActionTypes.IGNORED: AnalyticsEventTypes.DONATION_COMMENT_IGNORED,
    DonationProcessingActionTypes.MOD_COMMENT_EDITED: AnalyticsEventTypes.DONATION_MOD_COMMENT_EDITED,
    DonationProcessingActionTypes.GROUPS_CHANGED: AnalyticsEventTypes.DONATION_GROUPS_CHANGED,
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
        'groups': [g.name for g in donation.groups.all()],
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
    broadcast_donation_processing_action(request.user, donation, action)


# TODO:
# - do the permissions belong on the actions decorator or the class? The latter would be more DRY in theory
# - CanSendToReader should only apply if use_two_step_screening is turned on


class DonationViewSet(
    EventNestedMixin, WithSerializerPermissionsMixin, TrackerReadViewSet
):
    queryset = Donation.objects.select_related('donor').prefetch_related('groups')
    serializer_class = DonationSerializer
    filter_backends = [DonationFilter]
    permission_classes = [DonationQueryPermission]
    pagination_class = TrackerPagination

    @contextmanager
    def change_donation(self, action):
        donation = self.get_object()
        yield donation
        donation.save()
        _track_donation_processing_event(
            action=action, request=self.request, donation=donation
        )

    def get_queryset(self):
        """
        Processing only occurs on Donations that have settled their transaction
        and were not tests.
        """
        queryset = super().get_queryset().completed()
        if 'all_bids' in self.request.query_params or (
            self.request.method in ('PATCH', 'DELETE')
            and self.request.user.has_perm('tracker.view_bid')
        ):
            queryset = queryset.prefetch_related(
                'bids', 'bids__bid', 'bids__bid__parent'
            )
        else:
            queryset = queryset.prefetch_public_bids()
        return queryset

    def get_serializer(
        self,
        *args,
        mod_comments=False,
        all_comments=False,
        donors=False,
        groups=False,
        **kwargs,
    ):
        kwargs['with_mod_comments'] = (
            mod_comments or 'mod_comments' in self.request.query_params
        )
        kwargs['with_all_comments'] = (
            all_comments or 'all_comments' in self.request.query_params
        )
        kwargs['with_donor_ids'] = donors or 'donors' in self.request.query_params
        kwargs['with_groups'] = groups or 'groups' in self.request.query_params
        return super().get_serializer(*args, **kwargs)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[CanViewComments, CanViewDonations],
    )
    def unprocessed(self, request, *args, **kwargs):
        """
        Return a list of the oldest completed donations for the event which have
        not yet been processed in any way (e.g., are still PENDING for comment
        moderation).
        """
        donations = self.filter_queryset(self.get_queryset().to_process())
        page = self.paginate_queryset(donations)
        serializer = self.get_serializer(
            page, many=True, mod_comments=True, all_comments=True, groups=True
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[CanViewComments, CanViewDonations],
    )
    def flagged(self, request, *args, **kwargs):
        """
        Return a list of the oldest completed donations for the event which have
        been flagged for head review (e.g., are FLAGGED for read moderation).
        """
        donations = self.filter_queryset(self.get_queryset().to_approve())
        page = self.paginate_queryset(donations)
        serializer = self.get_serializer(
            page, many=True, mod_comments=True, all_comments=True, groups=True
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[CanViewComments, CanViewDonations],
    )
    def unread(self, request, *args, **kwargs):
        """
        Return a list of the oldest completed donations for the event which have
        been approved and sent to the reader (e.g., have a READY readstate, or
        FLAGGED/READY when one-step is turned on).
        """
        donations = self.filter_queryset(self.get_queryset().to_read())
        page = self.paginate_queryset(donations)
        serializer = self.get_serializer(
            page, many=True, mod_comments=True, all_comments=True, groups=True
        )
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['patch'])
    def unprocess(self, request, pk):
        """
        Reset the comment and read states for the donation.
        """
        with self.change_donation(
            action=DonationProcessingActionTypes.UNPROCESSED
        ) as donation:
            donation.commentstate = 'PENDING'
            donation.readstate = 'PENDING'
            data = self.get_serializer(
                donation, all_comments=True, mod_comments=True, groups=True
            ).data

        return Response(data)

    @action(detail=True, methods=['patch'])
    def approve_comment(self, request, pk):
        """
        Mark the comment for the donation as approved, but do not send it on to
        be read.
        """
        with self.change_donation(
            action=DonationProcessingActionTypes.APPROVED
        ) as donation:
            donation.commentstate = 'APPROVED'
            donation.readstate = 'IGNORED'
            data = self.get_serializer(donation, mod_comments=True, groups=True).data

        return Response(data)

    @action(detail=True, methods=['patch'])
    def deny_comment(self, request, pk):
        """
        Mark the comment for the donation as explicitly denied and ignored.
        """
        with self.change_donation(
            action=DonationProcessingActionTypes.DENIED
        ) as donation:
            donation.commentstate = 'DENIED'
            donation.readstate = 'IGNORED'
            data = self.get_serializer(
                donation, all_comments=True, mod_comments=True, groups=True
            ).data

        return Response(data)

    @action(detail=True, methods=['patch'])
    def flag(self, request, pk):
        """
        Mark the donation as approved, but flagged for head donations to review
        before sending to the reader. This should only be called when the event
        is using two-step screening.
        """
        if self.get_object().event.use_one_step_screening:
            raise ValidationError(
                'Event is using one-step screening, this endpoint should not be used'
            )
        with self.change_donation(
            action=DonationProcessingActionTypes.FLAGGED
        ) as donation:
            donation.commentstate = 'APPROVED'
            donation.readstate = 'FLAGGED'
            data = self.get_serializer(donation, mod_comments=True, groups=True).data

        return Response(data)

    @action(
        detail=True,
        methods=['patch'],
        permission_classes=[CanSendToReader],
    )
    def send_to_reader(self, request, pk):
        """
        Mark the donation as approved and send it directly to the reader.
        """
        with self.change_donation(
            action=DonationProcessingActionTypes.SENT_TO_READER
        ) as donation:
            donation.commentstate = 'APPROVED'
            donation.readstate = 'READY'
            data = self.get_serializer(donation, mod_comments=True, groups=True).data

        return Response(data)

    @action(detail=True, methods=['patch'])
    def pin(self, request, pk):
        """
        Mark the donation as pinned to the top of the reader's view.
        """
        with self.change_donation(
            action=DonationProcessingActionTypes.PINNED
        ) as donation:
            donation.pinned = True
            data = self.get_serializer(donation, mod_comments=True, groups=True).data

        return Response(data)

    @action(detail=True, methods=['patch'])
    def unpin(self, request, pk):
        """
        Umark the donation as pinned, returning it to a normal position in the donation list.
        """
        with self.change_donation(
            action=DonationProcessingActionTypes.UNPINNED
        ) as donation:
            donation.pinned = False
            data = self.get_serializer(donation, mod_comments=True, groups=True).data

        return Response(data)

    @action(detail=True, methods=['patch'])
    def read(self, request, pk):
        """
        Mark the donation as read, completing the donation's lifecycle.
        """
        with self.change_donation(
            action=DonationProcessingActionTypes.READ
        ) as donation:
            donation.readstate = 'READ'
            data = self.get_serializer(donation, mod_comments=True, groups=True).data

        return Response(data)

    @action(detail=True, methods=['patch'])
    def ignore(self, request, pk):
        """
        Mark the donation as ignored, completing the donation's lifecycle.
        """
        with self.change_donation(
            action=DonationProcessingActionTypes.IGNORED
        ) as donation:
            donation.readstate = 'IGNORED'
            data = self.get_serializer(donation, mod_comments=True, groups=True).data

        return Response(data)

    @action(detail=True, methods=['patch'])
    def comment(self, request, pk):
        """
        Add or edit the `modcomment` for the donation. Currently, donations only
        store a single comment; providing a new comment will override whatever
        comment currently exists.
        """
        comment = request.data.get('comment', None)
        if comment is None:
            return Response(
                {'comment': ErrorDetail('This field is required.', code='required')},
                status=400,
            )

        with self.change_donation(
            action=DonationProcessingActionTypes.MOD_COMMENT_EDITED
        ) as donation:
            donation.modcomment = comment
            data = self.get_serializer(donation, mod_comments=True, groups=True).data

        return Response(data)

    @action(
        detail=True,
        methods=['patch', 'delete'],
        url_path=r'groups/(?P<group>[-\w]+)',
        permission_classes=[tracker_permission('tracker.change_donation')],
        include_tracker_permissions=False,
    )
    def groups(self, request, pk, group, *args, **kwargs):
        """add or remove a group designation for a donation, returns the new list of groups"""
        donation = self.get_object()
        is_patch = request.method == 'PATCH'

        if request.user.has_perm('tracker.add_donationgroup') and is_patch:
            group, created = DonationGroup.objects.get_or_create_by_natural_key(group)
            # TODO: send a broadcast when a group is created this way
        else:
            try:
                group = DonationGroup.objects.get_by_natural_key(group)
            except DonationGroup.DoesNotExist:
                if is_patch:
                    raise ValidationError(
                        'specified group does not exist and you do not have permission to create new ones'
                    )
                else:
                    raise ValidationError('specified group does not exist')

        if is_patch:
            if group not in donation.groups.all():
                with self.change_donation(
                    DonationProcessingActionTypes.GROUPS_CHANGED
                ) as donation:
                    donation.groups.add(group)
        elif group in donation.groups.all():
            with self.change_donation(
                DonationProcessingActionTypes.GROUPS_CHANGED
            ) as donation:
                donation.groups.remove(group)

        return Response([g.name for g in donation.groups.all()])

    @action(detail=True, methods=['get'])
    def bids(self, request, *args, **kwargs):
        viewset = DonationBidViewSet(request=request, donation=self.get_object())
        viewset.initial(request, *args, **kwargs)
        return viewset.list(request, *args, **kwargs)
