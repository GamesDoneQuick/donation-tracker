from django.conf.urls import url

from . import views

app_name = 'tracker_ui'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^admin/', views.admin, name='admin'),
]
