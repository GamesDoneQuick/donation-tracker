from __future__ import annotations

import typing as t

from django.http import Http404
from rest_framework.permissions import (
    SAFE_METHODS,
    BasePermission,
    DjangoModelPermissions,
)
from rest_framework.request import Request

from tracker import models
from tracker.api import messages


def tracker_permission(
    permission_name: str, message: str = None, code: str = None
) -> type[BasePermission]:
    """
    generic permission check by permission name
    """

    class TrackerPermission(BasePermission):
        permission_name = ''

        def has_permission(self, request: Request, view: t.Callable):
            from tracker import settings

            if settings.DEBUG:
                from django.contrib.auth.models import Permission

                app_label, codename = self.permission_name.split('.')
                assert Permission.objects.filter(
                    content_type__app_label=app_label, codename=codename
                ).exists(), f'nonsense permission `{self.permission_name}`'
            if request.user is None:
                return False

            return request.user.has_perm(self.permission_name)

        def has_object_permission(self, request: Request, view: t.Callable, obj: t.Any):
            return self.has_permission(request, view)

    TrackerPermission.permission_name = permission_name

    if message:
        TrackerPermission.message = message
    if code:
        TrackerPermission.code = code

    return TrackerPermission


class EventArchivedPermission(BasePermission):
    message = messages.ARCHIVED_EVENT
    code = messages.ARCHIVED_EVENT_CODE

    def has_permission(self, request: Request, view: t.Callable):
        return request.method in SAFE_METHODS or not view.is_event_archived()

    def has_object_permission(self, request: Request, view: t.Callable, obj: t.Any):
        return request.method in SAFE_METHODS or not view.is_event_archived(obj)


class _DjangoModelViewPermissions(DjangoModelPermissions):
    perms_map = {
        **DjangoModelPermissions.perms_map,
        'GET': ['%(app_label)s.view_%(model_name)s'],
    }


class EventDraftPermission(BasePermission):
    message = messages.UNAUTHORIZED_DRAFT_EVENT
    code = messages.UNAUTHORIZED_DRAFT_EVENT_CODE

    def _has_view_permission(self, request: Request, view: t.Callable):
        if request.user.has_perm('tracker.view_event'):
            return True
        if perm := getattr(view, 'view_permission', None):
            return request.user.has_perm(perm)
        if _DjangoModelViewPermissions().has_permission(request, view):
            return True
        return False

    def has_permission(self, request: Request, view: t.Callable):
        return (not view.is_event_draft()) or self._has_view_permission(request, view)

    def has_object_permission(self, request: Request, view: t.Callable, obj: t.Any):
        return (not view.is_event_draft(obj)) or self._has_view_permission(
            request, view
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
                for p in ('change_bid', 'view_bid')
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
                for p in ('change_bid', 'view_bid')
            )
        )


class BidApprovalPermission(BasePermission):
    nested_permission = (
        tracker_permission('tracker.change_bid')
        | (
            tracker_permission('tracker.view_bid')
            & tracker_permission('tracker.approve_bid')
        )
    )()

    def has_object_permission(self, request: Request, view: t.Callable, obj: t.Any):
        # ensures that an attempt to approve/deny a nonsensical bid returns 404 instead of 403
        if obj.parent_id is None or not obj.parent.allowuseroptions:
            raise Http404
        return super().has_object_permission(
            request, view, obj
        ) and self.nested_permission.has_object_permission(request, view, obj)


class PrizeFeedPermission(BasePermission):
    PUBLIC_FEEDS = models.Prize.PUBLIC_FEEDS
    message = messages.UNAUTHORIZED_FEED
    code = messages.UNAUTHORIZED_FEED_CODE

    def has_permission(self, request: Request, view: t.Callable):
        feed = view.get_feed()
        return super().has_permission(request, view) and (
            feed is None
            or feed in self.PUBLIC_FEEDS
            or any(
                request.user.has_perm(f'tracker.{p}')
                for p in ('change_prize', 'view_prize')
            )
        )


class PrizeStatePermission(BasePermission):
    PUBLIC_STATES = models.Prize.PUBLIC_STATES
    message = messages.GENERIC_NOT_FOUND
    code = messages.UNAUTHORIZED_OBJECT_CODE

    def has_object_permission(self, request: Request, view: t.Callable, obj: t.Any):
        return super().has_object_permission(request, view, obj) and (
            obj.state in self.PUBLIC_STATES
            or any(
                request.user.has_perm(f'tracker.{p}')
                for p in ('change_prize', 'view_prize')
            )
        )


class DonationBidStatePermission(BasePermission):
    PUBLIC_STATES = models.Bid.PUBLIC_STATES
    message = messages.GENERIC_NOT_FOUND
    code = messages.UNAUTHORIZED_OBJECT_CODE

    def has_permission(self, request, view):
        has_perm = any(
            request.user.has_perm(f'tracker.{p}') for p in ('change_bid', 'view_bid')
        )
        return (
            super().has_permission(request, view)
            and has_perm
            or (
                ((view.bid is None or view.bid.state in self.PUBLIC_STATES))
                and ('all' not in request.query_params)
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


class DonationQueryPermission(BasePermission):
    def has_permission(self, request, view):
        if 'mod_comments' in request.query_params and not request.user.has_perm(
            'tracker.view_donation'
        ):
            return False
        if 'all_comments' in request.query_params and not request.user.has_perm(
            'tracker.view_comments'
        ):
            return False
        if 'donors' in request.query_params and not request.user.has_perm(
            'tracker.view_donor'
        ):
            return False
        if 'all_bids' in request.query_params and not request.user.has_perm(
            'tracker.view_bid'
        ):
            return False
        return True
