from django.urls import path

from ..views import donateviews
from . import views

app_name = 'tracker'
urlpatterns = [
    path('', views.index, name='index'),
    path('admin/<path:extra>', views.admin_redirect),
    path('donate/<slug:event>', donateviews.donate),
    path('events/<slug:event>/donate', views.donate, name='donate'),
    path('events/<path:extra>', views.index, name='events'),
]
