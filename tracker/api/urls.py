"""Define API URLs and documentation for our REST API."""

from django.urls import include, path
from rest_framework import routers

from tracker.api import views
from tracker.api.views import bids, donations, interview, me, milestone, run, runner

router = routers.DefaultRouter()


def event_nested_route(path, viewset, *, basename=None, feed=False):
    if basename is None:
        basename = router.get_default_basename(viewset)
    router.register(path, viewset, basename)
    if feed:
        router.register(
            r'events/(?P<event_pk>[^/.]+)/' + path + r'/feed_(?P<feed>\w+)',
            viewset,
            f'event-{basename}-feed',
        )
    router.register(
        r'events/(?P<event_pk>[^/.]+)/' + path, viewset, f'event-{basename}'
    )


# routers generate URLs based on the view sets, so that we don't need to do a bunch of stuff by hand
router.register(r'events', views.EventViewSet)
event_nested_route(r'bids', bids.BidViewSet, feed=True)
event_nested_route(r'runners', runner.RunnerViewSet)
event_nested_route(r'runs', run.SpeedRunViewSet)
event_nested_route(r'interviews', interview.InterviewViewSet)
event_nested_route(r'milestones', milestone.MilestoneViewSet)
router.register(r'donations', donations.DonationViewSet, basename='donations')
router.register(r'me', me.MeViewSet, basename='me')

# use the router-generated URLs, and also link to the browsable API
urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
app_name = 'tracker'
