from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^admin/', views.admin, name='admin'),
    url(r'^donate/(?P<event>\w+)$', views.donate, name='donate'),
]
