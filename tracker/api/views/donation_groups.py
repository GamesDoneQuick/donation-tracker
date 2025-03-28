import enum

from django.core.exceptions import ValidationError
from django.core.validators import validate_slug
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from tracker import logutil, models
from tracker.analytics import AnalyticsEventTypes, analytics
from tracker.api.serializers import AbstractTagField
from tracker.api.views import TrackerReadViewSet
from tracker.consumers.processing import broadcast_group_processing_action


class AbstractTagSerializer(serializers.Serializer, AbstractTagField):
    pass


class DonationGroupProcessingActionTypes(str, enum.Enum):
    CREATED = 'group_created'
    DELETED = 'group_deleted'


GROUP_ACTION_ANALYTICS_EVENTS = {
    DonationGroupProcessingActionTypes.CREATED: AnalyticsEventTypes.DONATION_GROUP_CREATED,
    DonationGroupProcessingActionTypes.DELETED: AnalyticsEventTypes.DONATION_GROUP_DELETED,
}


def _track_donation_group_processing_event(
    action: DonationGroupProcessingActionTypes,
    group: models.DonationGroup,
    request,
):
    # Add to local event audit log
    if action == DonationGroupProcessingActionTypes.CREATED:
        logutil.addition(request, group)
    else:
        logutil.deletion(request, group)

    # Track event to analytics database
    analytics.track(
        GROUP_ACTION_ANALYTICS_EVENTS[action],
        {
            'group': group.name,
            'user_id': request.user.pk,
        },
    )

    # Announce the action to all other processors
    broadcast_group_processing_action(request.user, group, action)


class DonationGroupViewSet(TrackerReadViewSet):
    queryset = models.DonationGroup.objects.all()

    def get_serializer(self, *args, **kwargs):
        return AbstractTagSerializer(*args, model=models.DonationGroup, **kwargs)

    def get_object(self):
        try:
            validate_slug(self.kwargs['pk'])
        except ValidationError:
            raise NotFound('invalid tag slug')
        return get_object_or_404(self.get_queryset(), name=self.kwargs['pk'].lower())

    def list(self, request, *args, **kwargs):
        return Response(g.name for g in self.get_queryset())

    def retrieve(self, request, *args, **kwargs):
        return Response(self.get_object().name)

    def update(self, request, *args, **kwargs):
        validate_slug(kwargs['pk'])
        m, c = models.DonationGroup.objects.get_or_create_by_natural_key(kwargs['pk'])
        if c:
            _track_donation_group_processing_event(
                DonationGroupProcessingActionTypes.CREATED, m, request
            )
        return Response(m.name, status=201 if c else 200)

    def destroy(self, request, *args, **kwargs):
        m = self.get_object()
        m.delete()
        _track_donation_group_processing_event(
            DonationGroupProcessingActionTypes.DELETED, m, request
        )
        return Response(status=204)
