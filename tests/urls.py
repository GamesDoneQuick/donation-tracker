import ajax_select.urls
from django.contrib import admin
from django.urls import include, path

import tracker.urls

urlpatterns = [
    path('tracker/', include(tracker.urls)),
    path('admin/lookups/', include(ajax_select.urls)),
    path('admin/', admin.site.urls),
]
