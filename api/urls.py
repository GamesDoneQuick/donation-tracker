"""Define API URLs and documentation for our REST API."""

from django.conf.urls import url, include
from rest_framework import routers

from tracker.api import views

# routers generate URLs based on the view sets, so that we don't need to do a bunch of stuff by hand
router = routers.DefaultRouter()
router.register(r'events', views.EventViewSet)
router.register(r'runners', views.RunnerViewSet)
router.register(r'runs', views.SpeedRunViewSet)

# use the router-generated URLs, and also link to the browsable API
urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]
