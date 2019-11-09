from django.conf.urls import url

from .views import api

urlpatterns = [
    url(r'^$', api.root, name='root'),
    url(r'^search/$', api.search, name='search'),
    url(r'^add/$', api.add, name='add'),
    url(r'^edit/$', api.edit, name='edit'),
    url(r'^delete/$', api.delete, name='delete'),
    url(r'^command/$', api.command, name='command'),
    url(r'^me/$', api.me, name='me'),
]
