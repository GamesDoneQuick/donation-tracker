from django.db.models import Prefetch, Q

from tracker.api.pagination import TrackerPagination
from tracker.api.permissions import tracker_permission
from tracker.api.serializers import DonorSerializer
from tracker.api.views import EventNestedMixin, TrackerReadViewSet
from tracker.models import Donor, DonorCache


class DonorViewSet(EventNestedMixin, TrackerReadViewSet):
    queryset = Donor.objects.all()
    pagination_class = TrackerPagination
    permission_classes = [tracker_permission('tracker.view_donor')]
    serializer_class = DonorSerializer

    def _include_totals(self):
        return 'include_totals' in self.request.query_params

    def get_queryset(self):
        queryset = super().get_queryset()
        if self._include_totals():
            if event := self.get_event_from_request():
                dc_queryset = DonorCache.objects.filter(
                    Q(event__isnull=True) | Q(event=event)
                )
            else:
                dc_queryset = DonorCache.objects.all()
            queryset = queryset.prefetch_related(
                Prefetch('cache', queryset=dc_queryset)
            )
        return queryset

    def get_serializer(self, *args, **kwargs):
        if self._include_totals():
            kwargs['include_totals'] = True
        return super().get_serializer(*args, **kwargs)

    def get_event_filter(self, queryset, event):
        if event:
            queryset = queryset.filter(
                id__in=(
                    d['id']
                    for d in queryset.filter(donation__event=event)
                    .distinct()
                    .values('id')
                )
            )
        return queryset
