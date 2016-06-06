from django.shortcuts import render
from tracker.models import Event
from django.views.decorators.csrf import csrf_protect
from django.conf import settings
from webpack_manifest import webpack_manifest

import os

@csrf_protect
def index(request):
    webpack = bool(request.META.get('HTTP_X_WEBPACK', False))
    admin = webpack_manifest.load(
        os.path.abspath(os.path.join(os.path.dirname(__file__), 'ui-admin.manifest.json')),
        '/webpack' if webpack else settings.STATIC_URL,
        debug=settings.DEBUG,
        timeout=60,
        read_retry=None
    )

    return render(request, 'tracker_ui/index.html', dictionary={'event': Event.objects.latest(), 'events': Event.objects.all(), 'admin': admin})
