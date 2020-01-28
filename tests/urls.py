import ajax_select.urls
from django.conf.urls import include, url
from django.contrib import admin

import tracker.urls

urlpatterns = [
    url(r'^tracker/', include(tracker.urls)),
    url(r'^admin/lookups/', include(ajax_select.urls)),
    url(r'^admin/', admin.site.urls),
]
