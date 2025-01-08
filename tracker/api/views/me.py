from rest_framework import serializers, viewsets
from rest_framework.response import Response

from tracker.api.views import RemoveBrowsableMixin


class MeSerializer(serializers.Serializer):
    username = serializers.CharField()
    superuser = serializers.BooleanField()
    staff = serializers.BooleanField()
    permissions = serializers.ListField(child=serializers.CharField())


class MeViewSet(RemoveBrowsableMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        """
        Return information about the user that made the request.
        """

        if request.user.is_anonymous or not request.user.is_active:
            return Response(status=403)

        me = MeSerializer(
            {
                'username': request.user.username,
                'superuser': request.user.is_superuser,
                'staff': request.user.is_staff,
                'permissions': list(request.user.get_all_permissions()),
            }
        )

        return Response(me.data)
