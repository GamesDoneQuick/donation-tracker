from django.contrib import admin
from django.http import JsonResponse

site = admin.site

__all__ = [
    'gone',
]


def gone(request, *args, **kwargs):
    return JsonResponse(
        data={'detail': 'v1 API is retired, please use v2 API instead'}, status=410
    )
