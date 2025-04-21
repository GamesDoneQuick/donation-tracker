import contextlib

from django.contrib import admin
from django.http import JsonResponse
from django.urls import NoReverseMatch

from tracker.compat import reverse

site = admin.site

__all__ = [
    'gone',
]

modelmap = {
    'allbids': 'bid-tree',
    'run': 'speedrun-list',
    'runner': 'talent-list',
    'headset': 'talent-list',
}


def gone(request, *args, **kwargs):
    data = {'detail': 'v1 API is retired, please use v2 API instead'}
    if t := request.GET.get('type', None):
        t = modelmap.get(t, f'{t}-list')
        args = []
        if 'event' in request.GET:
            t = 'event-' + t
            args = request.GET['event']
        with contextlib.suppress(NoReverseMatch):
            data['hint'] = reverse(f'tracker:api_v2:{t}', args=args)
    return JsonResponse(data=data, status=410)
