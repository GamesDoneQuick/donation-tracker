import json
import os
from decimal import Decimal

from django.conf import settings
from django.core import serializers
from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import render
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_protect
from webpack_manifest import webpack_manifest

from tracker import filters, viewutil
from tracker.models import Event
from tracker.views.donateviews import process_form


@csrf_protect
def index(request):
    raise Http404 # nothing yet
    bundle = webpack_manifest.load(
        os.path.abspath(os.path.join(os.path.dirname(__file__), 'ui-tracker.manifest.json')),
        settings.STATIC_URL,
        debug=settings.DEBUG,
        timeout=60,
        read_retry=None
    )

    return render(
        request,
        'tracker_ui/index.html',
        dictionary={
            'event': Event.objects.latest(),
            'events': Event.objects.all(),
            'bundle': bundle.index,
            'root_path': reverse('tracker_ui:index'),
            'app': 'IndexApp',
            'props': mark_safe(json.dumps({}, ensure_ascii=False, cls=serializers.json.DjangoJSONEncoder)),
        },
    )


@csrf_protect
def admin(request):
    bundle = webpack_manifest.load(
        os.path.abspath(os.path.join(os.path.dirname(__file__), 'ui-tracker.manifest.json')),
        settings.STATIC_URL,
        debug=settings.DEBUG,
        timeout=60,
        read_retry=None
    )

    return render(
        request,
        'tracker_ui/index.html',
        dictionary={
            'event': Event.objects.latest(),
            'events': Event.objects.all(),
            'bundle': bundle.admin,
            'root_path': reverse('tracker_ui:admin'),
            'app': 'AdminApp',
            'form_errors': {},
            'props': mark_safe(json.dumps({}, ensure_ascii=False, cls=serializers.json.DjangoJSONEncoder)),
        },
    )
