import tracker.viewutil as viewutil
import tracker.models

import settings

import django
from django.utils import translation
from django.shortcuts import render
from django.http import HttpResponse
from django.db import connection

import datetime
import json
import sys

def dv():
  return str(django.VERSION[0]) + '.' + str(django.VERSION[1]) + '.' + str(django.VERSION[2])

def pv():
  return str(sys.version_info[0]) + '.' + str(sys.version_info[1]) + '.' + str(sys.version_info[2])

def fixorder(queryset, orderdict, sort, order):
  queryset = queryset.order_by(*orderdict[sort])
  if order == -1:
    queryset = queryset.reverse()
  return queryset

def tracker_response(request=None, template='tracker/index.html', qdict=None, status=200):
  starttime = datetime.datetime.now()
  language = translation.get_language_from_request(request)
  translation.activate(language)
  request.LANGUAGE_CODE = translation.get_language()
  profile = None
  qdict = qdict or {}
  qdict.update({
    'djangoversion' : dv(),
    'pythonversion' : pv(),
    'user' : request.user,
    'profile' : profile,
    'next' : request.POST.get('next', request.GET.get('next', request.path)),
    'starttime' : starttime,
    'events': tracker.models.Event.objects.all(),
    })
  qdict.setdefault('event',viewutil.get_event(None))
  qdict.setdefault('user',request.user)
  try:
    resp = render(request, template, dictionary=qdict, status=status)
    if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
      return HttpResponse(json.dumps(connection.queries, ensure_ascii=False, indent=1),content_type='application/json;charset=utf-8')
    return resp
  except Exception,e:
    if request.user.is_staff and not settings.DEBUG:
      return HttpResponse(unicode(type(e)) + '\n\n' + unicode(e), mimetype='text/plain', status=500)
    raise