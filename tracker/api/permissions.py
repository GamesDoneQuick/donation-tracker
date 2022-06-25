import typing as t

from rest_framework.request import Request
from rest_framework.permissions import BasePermission


def tracker_permission(permission_name: str):
    class TrackerPermission(BasePermission):
        def has_permission(self, request: Request, view: t.Callable):
            if request.user is None:
                return False

            return request.user.has_perm(permission_name)

        def has_object_permission(self, request: Request, view: t.Callable, obj: t.Any):
            return self.has_permission(request, view)

    return TrackerPermission
