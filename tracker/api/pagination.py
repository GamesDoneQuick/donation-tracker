from rest_framework.exceptions import ParseError
from rest_framework.pagination import LimitOffsetPagination

from tracker import settings


class TrackerPagination(LimitOffsetPagination):
    default_limit = settings.TRACKER_PAGINATION_LIMIT
    max_limit = settings.TRACKER_PAGINATION_LIMIT

    def get_limit(self, request):
        try:
            limit = int(
                request.query_params.get(self.limit_query_param, self.default_limit)
            )
        except ValueError:
            raise ParseError('Malformed limit parameter')
        if limit < 0:
            raise ParseError('Malformed limit parameter')
        if limit > self.max_limit:
            raise ParseError(f'Page limit too high, limit is {self.max_limit}')
        return limit

    def get_offset(self, request):
        try:
            offset = int(request.query_params.get(self.offset_query_param, 0))
        except ValueError:
            raise ParseError('Malformed offset parameter')
        if offset < 0:
            raise ParseError('Malformed offset parameter')
        return offset
