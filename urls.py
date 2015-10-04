from django.conf.urls import patterns, include, url

urlpatterns = patterns('tracker_ui.views',
                       url('', 'index'),
                       )
