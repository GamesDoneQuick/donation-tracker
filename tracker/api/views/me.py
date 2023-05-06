from rest_framework import serializers, viewsets
from rest_framework.response import Response


class MeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    superuser = serializers.BooleanField()
    staff = serializers.BooleanField()
    permissions = serializers.ListField(child=serializers.CharField())


class MeViewSet(viewsets.GenericViewSet):
    def list(self, request):
        """
        Return information about the user that made the request.
        """

        if request.user.is_anonymous or not request.user.is_active:
            return Response(status=403)

        me = MeSerializer(
            {
                'id': request.user.id,
                'username': request.user.username,
                'superuser': request.user.is_superuser,
                'staff': request.user.is_staff,
                'permissions': list(request.user.get_all_permissions()),
            }
        )

        return Response(me.data)
