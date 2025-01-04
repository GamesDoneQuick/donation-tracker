from django.urls import path

from tracker.views import api

app_name = 'tracker'
urlpatterns = [
    path('', api.root, name='root'),
    path('search/', api.search, name='search'),
    path('add/', api.gone, name='add'),
    path('edit/', api.gone, name='edit'),
    path('delete/', api.gone, name='delete'),
    path('command/', api.command, name='command'),
    path('me/', api.me, name='me'),
    # moved over from private repo, stopgap until v2 is ready
    path('ads/<int:event>/', api.ads, name='ads'),
    path('interviews/<int:event>/', api.interviews, name='interviews'),
]
