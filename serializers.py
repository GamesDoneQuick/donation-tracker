from django.core.serializers.json import Serializer as JSONSerializer
from django.db import models

from tracker.models import Prize

_ExtraFields = {
    Prize: ['start_draw_time', 'end_draw_time'],
}


class TrackerSerializer(JSONSerializer):
    def __init__(self, Model, request):
        self.Model = Model
        self.request = request

    def handle_field(self, obj, field):
        if isinstance(field, models.FileField):
            value = field.value_from_object(obj)
            self._current[field.name] = value.url if value else ''
        else:
            super(TrackerSerializer, self).handle_field(obj, field)

    def get_dump_object(self, obj):
        data = super(TrackerSerializer, self).get_dump_object(obj)
        for extra_field in _ExtraFields.get(self.Model, []):
            prop = getattr(obj, extra_field)
            if callable(prop):
                prop = prop()
            data['fields'][extra_field] = prop
        absolute_url = getattr(obj, 'get_absolute_url', None)
        if callable(absolute_url):
            data['fields']['canonical_url'] = self.request.build_absolute_uri(
                absolute_url()
            )
        return data
