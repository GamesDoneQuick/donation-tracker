import json
import sys

import django
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import translation
from django.utils.cache import patch_cache_control

import tracker.models
import tracker.viewutil as viewutil
from tracker import settings


def dv():
    return (
        str(django.VERSION[0])
        + '.'
        + str(django.VERSION[1])
        + '.'
        + str(django.VERSION[2])
    )


def pv():
    return (
        str(sys.version_info[0])
        + '.'
        + str(sys.version_info[1])
        + '.'
        + str(sys.version_info[2])
    )


def fixorder(queryset, orderdict, sort, order):
    if sort in orderdict:
        queryset = queryset.order_by(*orderdict[sort])
    if order == -1:
        queryset = queryset.reverse()
    return queryset


def tracker_context(request, qdict=None):
    language = translation.get_language_from_request(request)
    translation.activate(language)
    request.LANGUAGE_CODE = translation.get_language()
    qdict = qdict or {}
    qdict.update(
        {
            'user': request.user,
            'events': tracker.models.Event.objects.all(),
            'settings': {
                'TRACKER_SWEEPSTAKES_URL': settings.TRACKER_SWEEPSTAKES_URL,
                'TRACKER_LOGO': settings.TRACKER_LOGO,
                'TRACKER_CONTRIBUTORS_URL': settings.TRACKER_CONTRIBUTORS_URL,
            },
        }
    )
    qdict.setdefault('event', viewutil.get_event(None))
    return qdict


def tracker_response(
    request, template='tracker/index.html', qdict=None, status=200, delegate=None
):
    qdict = tracker_context(request, qdict)
    if delegate:
        resp = delegate(request, template, context=qdict, status=status)
    else:
        resp = render(request, template, context=qdict, status=status)
    if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
        resp = HttpResponse(
            json.dumps(connection.queries, ensure_ascii=False, indent=1),
            content_type='application/json;charset=utf-8',
        )
    cache_control = {}
    if request.user.is_anonymous:
        cache_control['public'] = True
    else:
        cache_control['private'] = True
        cache_control['max-age'] = 0
    patch_cache_control(resp, **cache_control)
    return resp
