from django.urls import path

from tracker.views import api

app_name = 'tracker'
urlpatterns = [
    path('', api.gone, name='root'),
    path('search/', api.gone, name='search'),
    path('add/', api.gone, name='add'),
    path('edit/', api.gone, name='edit'),
    path('delete/', api.gone, name='delete'),
    path('command/', api.gone, name='command'),
    path('me/', api.gone, name='me'),
    path('ads/<int:event>/', api.gone, name='ads'),
    path('interviews/<int:event>/', api.gone, name='interviews'),
]
