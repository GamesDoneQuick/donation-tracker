"""Define API URLs and documentation for our REST API."""

from django.urls import include, path
from rest_framework import routers

import tracker.api.views.run
from tracker.api import views
from tracker.api.views import bids, donations, me

router = routers.DefaultRouter()


def event_nested_route(path, viewset, *, feed=False, **kwargs):
    router.register(path, viewset)
    if feed:
        router.register(
            r'events/(?P<event_pk>[^/.]+)/' + path + r'/feed_(?P<feed>\w+)',
            viewset,
            **kwargs,
        )
    router.register(r'events/(?P<event_pk>[^/.]+)/' + path, viewset, **kwargs)


# routers generate URLs based on the view sets, so that we don't need to do a bunch of stuff by hand
router.register(r'events', views.EventViewSet)
event_nested_route(r'bids', bids.BidViewSet, feed=True)
router.register(r'runners', views.RunnerViewSet)
event_nested_route(r'runs', tracker.api.views.run.SpeedRunViewSet)
router.register(r'donations', donations.DonationViewSet, basename='donations')
router.register(r'me', me.MeViewSet, basename='me')

# use the router-generated URLs, and also link to the browsable API
urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
app_name = 'tracker'
