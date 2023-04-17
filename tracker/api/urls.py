"""Define API URLs and documentation for our REST API."""

from django.urls import include, path
from rest_framework import routers

from tracker.api import views
from tracker.api.views import donations, me

# routers generate URLs based on the view sets, so that we don't need to do a bunch of stuff by hand
router = routers.DefaultRouter()
router.register(r'events', views.EventViewSet)
router.register(r'runners', views.RunnerViewSet)
router.register(r'runs', views.SpeedRunViewSet)
router.register(r'donations', donations.DonationViewSet, basename='donations')
router.register(r'me', me.MeViewSet, basename='me')

# use the router-generated URLs, and also link to the browsable API
urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
app_name = 'tracker'
