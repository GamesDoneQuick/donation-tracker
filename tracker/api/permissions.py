import typing as t

from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import (
    SAFE_METHODS,
    BasePermission,
    DjangoModelPermissionsOrAnonReadOnly,
)
from rest_framework.request import Request

from tracker.api import messages
from tracker.models import Bid

UNAUTHORIZED_LOCKED_EVENT = 'unauthorized_locked_event'
UNAUTHORIZED_FEED = 'unauthorized_feed'
UNAUTHORIZED_OBJECT = 'unauthorized_object'


def tracker_permission(permission_name: str):
    class TrackerPermission(BasePermission):
        def has_permission(self, request: Request, view: t.Callable):
            if request.user is None:
                return False

            return request.user.has_perm(permission_name)

        def has_object_permission(self, request: Request, view: t.Callable, obj: t.Any):
            return self.has_permission(request, view)

    return TrackerPermission


class EventLockedPermission(DjangoModelPermissionsOrAnonReadOnly):
    message = _('You do not have permission to edit locked events.')
    code = UNAUTHORIZED_LOCKED_EVENT

    def has_permission(self, request: Request, view: t.Callable):
        return super().has_permission(request, view) and (
            request.method in SAFE_METHODS
            or request.user.has_perm('tracker.edit_locked_events')
            or not view.is_event_locked(request)
        )

    def has_object_permission(self, request: Request, view: t.Callable, obj: t.Any):
        return super().has_object_permission(request, view, obj) and (
            request.method in SAFE_METHODS
            or request.user.has_perm('tracker.can_edit_locked_events')
            or not obj.event.locked
        )


class BidFeedPermission(BasePermission):
    PUBLIC_FEEDS = Bid.PUBLIC_FEEDS
    message = _('You do not have permission to view that feed.')
    code = UNAUTHORIZED_FEED

    def has_permission(self, request: Request, view: t.Callable):
        feed = view.get_feed()
        return super().has_permission(request, view) and (
            feed is None
            or feed in self.PUBLIC_FEEDS
            or request.user.has_perm('tracker.view_hidden_bid')
        )


class BidStatePermission(BasePermission):
    PUBLIC_STATES = Bid.PUBLIC_STATES
    message = messages.GENERIC_NOT_FOUND
    code = UNAUTHORIZED_OBJECT

    def has_object_permission(self, request: Request, view: t.Callable, obj: t.Any):
        return super().has_object_permission(request, view, obj) and (
            obj.state in self.PUBLIC_STATES
            or request.user.has_perm('tracker.view_hidden_bids')
        )
