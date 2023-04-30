from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from tracker import settings
from tracker.api.permissions import tracker_permission
from tracker.api.serializers import DonationProcessActionSerializer, DonationSerializer
from tracker.api.views.donations import (
    DonationChangeManager,
    DonationProcessingActionTypes,
)
from tracker.models import DonationProcessAction

CanChangeDonation = tracker_permission('tracker.change_donation')
CanViewAllProcessActions = tracker_permission('tracker.view_all_process_actions')


class ProcessActionViewSet(viewsets.GenericViewSet):
    queryset = DonationProcessAction.objects
    serializer_class = DonationProcessActionSerializer
    permission_classes = [CanChangeDonation]

    def list(self, request):
        """
        Return a list of the most recent DonationProcessActions for the event.
        If the requesting user has permissions to see processing actions from
        all users, they will all be returned. Otherwise, only actions performed
        by the user will be returned. The maximum number of actions returned is
        determined by TRACKER_PAGINATION_LIMIT.
        """
        limit = settings.TRACKER_PAGINATION_LIMIT
        actions = self.get_queryset().prefetch_related(
            'actor', 'donation', 'originating_action'
        )

        # If the user cannot see all process actions, filter down to just theirs.
        if not CanViewAllProcessActions().has_permission(request, self):
            actions = actions.filter(actor=request.user)

        actions = actions[0:limit]
        serializer = self.get_serializer(actions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def undo(self, request, pk):
        """
        Reverses the given action on the target donation, so long as the current
        state of the donation matches the action's `to_state`. If `force` is
        as a body param, the action will be reversed regardless of the current
        state.
        """
        action = get_object_or_404(DonationProcessAction, pk=pk)

        # Ensure the requesting user can affect this action.
        if (
            action.actor != request.user
            and not CanViewAllProcessActions().has_permission(request, self)
        ):
            raise PermissionDenied()

        manager = DonationChangeManager(request, action.donation.pk, DonationSerializer)
        manager.change_donation_state(
            action=DonationProcessingActionTypes.UNDONE,
            to_state=action.from_state,
            originating_action=action,
        )
        return Response(self.get_serializer(manager.action_record).data)
