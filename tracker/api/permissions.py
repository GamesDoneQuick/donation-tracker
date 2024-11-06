from __future__ import annotations

import typing as t

from rest_framework.permissions import (
    SAFE_METHODS,
    BasePermission,
    DjangoModelPermissionsOrAnonReadOnly,
)
from rest_framework.request import Request

from tracker import models
from tracker.api import messages


def tracker_permission(permission_name: str) -> type[BasePermission]:
    """
    generic permission check by permission name
    """

    class TrackerPermission(BasePermission):
        def has_permission(self, request: Request, view: t.Callable):
            if request.user is None:
                return False

            return request.user.has_perm(permission_name)

        def has_object_permission(self, request: Request, view: t.Callable, obj: t.Any):
            return self.has_permission(request, view)

    return TrackerPermission


class EventLockedPermission(DjangoModelPermissionsOrAnonReadOnly):
    message = messages.UNAUTHORIZED_LOCKED_EVENT
    code = messages.UNAUTHORIZED_LOCKED_EVENT_CODE

    def has_permission(self, request: Request, view: t.Callable):
        return super().has_permission(request, view) and (
            request.method in SAFE_METHODS
            or request.user.has_perm('tracker.can_edit_locked_events')
            or not view.is_event_locked()
        )

    def has_object_permission(self, request: Request, view: t.Callable, obj: t.Any):
        return super().has_object_permission(request, view, obj) and (
            request.method in SAFE_METHODS
            or request.user.has_perm('tracker.can_edit_locked_events')
            or not view.is_event_locked(obj)
        )


class BidFeedPermission(BasePermission):
    PUBLIC_FEEDS = models.Bid.PUBLIC_FEEDS
    message = messages.UNAUTHORIZED_FEED
    code = messages.UNAUTHORIZED_FEED_CODE

    def has_permission(self, request: Request, view: t.Callable):
        feed = view.get_feed()
        return super().has_permission(request, view) and (
            feed is None
            or feed in self.PUBLIC_FEEDS
            or any(
                request.user.has_perm(f'tracker.{p}')
                for p in ('view_hidden_bid', 'change_bid', 'view_bid')
            )
        )


class BidStatePermission(BasePermission):
    PUBLIC_STATES = models.Bid.PUBLIC_STATES
    message = messages.GENERIC_NOT_FOUND
    code = messages.UNAUTHORIZED_OBJECT_CODE

    def has_object_permission(self, request: Request, view: t.Callable, obj: t.Any):
        return super().has_object_permission(request, view, obj) and (
            obj.state in self.PUBLIC_STATES
            or any(
                request.user.has_perm(f'tracker.{p}')
                for p in ('view_hidden_bid', 'change_bid', 'view_bid')
            )
        )


class TechNotesPermission(BasePermission):
    message = messages.UNAUTHORIZED_FIELD
    code = messages.UNAUTHORIZED_FIELD_CODE

    def has_permission(self, request: Request, view: t.Callable):
        return super().has_permission(request, view) and (
            'tech_notes' not in request.query_params
            or request.user.has_perm('tracker.can_view_tech_notes')
        )


class CanSendToReader(BasePermission):
    message = messages.UNAUTHORIZED_FIELD_MODIFICATION
    code = messages.UNAUTHORIZED_FIELD_MODIFICATION_CODE

    def has_object_permission(self, request, view, obj):
        return super().has_object_permission(
            request, view, obj
        ) and obj.user_can_send_to_reader(request.user)


# noinspection PyPep8Naming
def PrivateListGenericPermission(model_name: str):
    """
    generic check that a user can request `all` models with the corresponding view permission
    """

    class PrivateListPermission(BasePermission):
        message = messages.UNAUTHORIZED_FILTER_PARAM
        code = messages.UNAUTHORIZED_FILTER_PARAM_CODE

        def has_permission(self, request, view):
            return (
                view.detail
                or 'all' not in request.query_params
                or request.user.has_perm(f'tracker.view_{model_name}')
            )

    return PrivateListPermission


# noinspection PyPep8Naming
def PrivateDetailGenericPermission(
    model_name: str, is_public: t.Callable[[models.Model], bool]
):
    """
    generic check that a user can request "private" model details with the corresponding view permission
    """

    class PrivateDetailPermission(BasePermission):
        message = messages.GENERIC_NOT_FOUND
        code = messages.UNAUTHORIZED_OBJECT_CODE

        def has_object_permission(self, request, view, obj):
            return is_public(obj) or request.user.has_perm(f'tracker.view_{model_name}')

    return PrivateDetailPermission


# noinspection PyPep8Naming
def PrivateGenericPermissions(
    model_name: str, is_public: t.Callable[[models.Model], bool]
):
    """
    combined generic check for both list and detail permissions

    e.g.
    permission_classes = [*PrivateGenericPermissions('interview', lambda o: o.public)]
    """
    # TODO: can't use `&` here to combine permissions because then the codes get lost, feature request perhaps?
    return [
        PrivateListGenericPermission(model_name),
        PrivateDetailGenericPermission(model_name, is_public),
    ]
