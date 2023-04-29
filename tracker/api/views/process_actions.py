from rest_framework import viewsets
from rest_framework.decorators import permission_classes
from rest_framework.response import Response

from tracker import settings
from tracker.api.permissions import tracker_permission
from tracker.api.serializers import DonationProcessActionSerializer
from tracker.models import DonationProcessAction

CanChangeDonation = tracker_permission('tracker.change_donation')
CanViewAllProcessActions = tracker_permission('tracker.view_all_process_actions')


class ProcessActionViewSet(viewsets.GenericViewSet):
    queryset = DonationProcessAction.objects
    serializer_class = DonationProcessActionSerializer

    @permission_classes([CanChangeDonation])
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
            actions.filter(actor=request.user)

        actions = actions[0:limit]
        serializer = self.get_serializer(actions, many=True)
        return Response(serializer.data)
