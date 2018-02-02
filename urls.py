from django.conf.urls import url

from . import views

app_name = 'tracker_ui'
urlpatterns = [
    url('', views.index, name='index'),
]
