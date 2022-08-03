import ajax_select.urls
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

import tracker.urls


def empty(request):
    return HttpResponse('')


urlpatterns = [
    path('tracker/', include(tracker.urls)),
    path('admin/lookups/', include(ajax_select.urls)),
    path('admin/', admin.site.urls),
    path('favicon.ico', empty),
]

urlpatterns += staticfiles_urlpatterns()
