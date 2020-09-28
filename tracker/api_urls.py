from django.urls import path

from tracker.views import api

app_name = 'tracker'
urlpatterns = [
    path('', api.root, name='root'),
    path('search/', api.search, name='search'),
    path('add/', api.add, name='add'),
    path('edit/', api.edit, name='edit'),
    path('delete/', api.delete, name='delete'),
    path('command/', api.command, name='command'),
    path('me/', api.me, name='me'),
    # moved over from private repo, stopgap until v2 is ready
    path('ads/<int:event>/', api.ads),
    path('interstitial/', api.interstitial, name='interstitial'),
    path('interviews/<int:event>/', api.interviews),
    path('hosts/<int:event>/', api.hosts),
]
