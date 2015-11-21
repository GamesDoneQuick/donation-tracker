from django.conf.urls import patterns, url, include
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^donation_tracker/', include('tracker.urls')),
    url(r'^admin/lookups/', include('ajax_select.urls')),
    url(r'^admin/', include(admin.site.urls)),
)
