from django.urls import path

from . import views

app_name = 'tracker'
urlpatterns = [
    path('', views.index, name='index'),
    path('admin/', views.admin, name='admin'),
    path('admin/v2/<path:extra>', views.admin_v2, name='admin_v2'),
    path('admin/<path:extra>', views.admin, name='admin'),
    path('donate/<slug:event>', views.donate, name='donate'),
    path('events/<path:extra>', views.index, name='events'),
]
