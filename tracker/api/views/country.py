import re

from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.generics import get_object_or_404

from tracker.api.pagination import TrackerPagination
from tracker.api.serializers import CountryRegionSerializer, CountrySerializer
from tracker.api.views import TrackerReadViewSet
from tracker.models import Country, CountryRegion


class CountryViewSet(TrackerReadViewSet):
    serializer_class = CountrySerializer
    pagination_class = TrackerPagination
    queryset = Country.objects.all()
    lookup_field = 'numeric_or_alpha'

    def get_object(self):
        queryset = self.get_queryset()
        pk = self.kwargs['numeric_or_alpha']
        if re.match('[0-9]{3}', pk):
            return get_object_or_404(queryset, numeric=pk)
        elif re.match('[A-Z]{2,3}', pk):
            return get_object_or_404(queryset, Q(alpha2=pk) | Q(alpha3=pk))
        raise NotFound(
            detail='Provide either an ISO 3166-1 numeric, alpha2, or alpha3 code',
            code='invalid_lookup',
        )

    @action(detail=True)
    def regions(self, request, *args, **kwargs):
        viewset = CountryRegionViewSet(request=request, country=self.get_object())
        viewset.initial(request, *args, **kwargs)
        return viewset.list(request, *args, **kwargs)


class CountryRegionViewSet(TrackerReadViewSet):
    serializer_class = CountryRegionSerializer
    pagination_class = TrackerPagination
    queryset = CountryRegion.objects.select_related('country')

    def __init__(self, country=None, *args, **kwargs):
        self.country = country
        super().__init__(*args, **kwargs)

    def filter_queryset(self, queryset):
        if self.country:
            queryset = queryset.filter(country=self.country)
        return queryset
