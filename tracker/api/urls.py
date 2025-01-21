"""Define API URLs and documentation for our REST API."""

from django.urls import include, path
from rest_framework import routers

from tracker.api import views
from tracker.api.views import (
    ad,
    bids,
    country,
    donations,
    donors,
    interview,
    me,
    milestone,
    prize,
    run,
    talent,
)

router = routers.DefaultRouter()


def event_nested_route(path, viewset, *, basename=None, feed=False):
    if basename is None:
        basename = router.get_default_basename(viewset)
    if feed:
        router.register(
            r'events/(?P<event_pk>[^/.]+)/' + path + r'/feed_(?P<feed>\w+)',
            viewset,
            f'event-{basename}-feed',
        )
        router.register(
            path + r'/feed_(?P<feed>\w+)',
            viewset,
            f'{basename}-feed',
        )
    router.register(
        r'events/(?P<event_pk>[^/.]+)/' + path, viewset, f'event-{basename}'
    )
    router.register(path, viewset, basename)


# routers generate URLs based on the view sets, so that we don't need to do a bunch of stuff by hand
router.register(r'events', views.EventViewSet)
event_nested_route(r'bids', bids.BidViewSet, feed=True)
event_nested_route(r'talent', talent.TalentViewSet)
event_nested_route(r'runs', run.SpeedRunViewSet)
event_nested_route(r'ads', ad.AdViewSet)
event_nested_route(r'interviews', interview.InterviewViewSet)
event_nested_route(r'milestones', milestone.MilestoneViewSet)
event_nested_route(r'prizes', prize.PrizeViewSet, feed=True)
event_nested_route(r'donors', donors.DonorViewSet)
event_nested_route(r'donations', donations.DonationViewSet)
router.register(r'me', me.MeViewSet, basename='me')
router.register(r'countries', country.CountryViewSet)
router.register(r'regions', country.CountryRegionViewSet, basename='region')

# use the router-generated URLs, and also link to the browsable API
urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
app_name = 'tracker'
