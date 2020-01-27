import ajax_select.urls
from django.conf.urls import include, url
from django.contrib import admin

import tracker.urls
from tracker.views import logout

urlpatterns = [
    url(r'^tracker/', include(tracker.urls)),
    url(r'^admin/lookups/', include(ajax_select.urls)),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^logout/', logout),
]
