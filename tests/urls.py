from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.http import HttpResponse
from django.urls import include, path

import tracker.urls


def empty(request):
    return HttpResponse('')


urlpatterns = [
    path('tracker/', include(tracker.urls)),
    path('admin/', admin.site.urls),
    path('favicon.ico', empty),
]

urlpatterns += staticfiles_urlpatterns()
