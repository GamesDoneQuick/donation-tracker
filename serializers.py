from django.db import models
from django.core.serializers.json import Serializer as JSONSerializer

from tracker.models import Prize

_ExtraFields = {
    Prize: ['start_draw_time', 'end_draw_time'],
}


class TrackerSerializer(JSONSerializer):
    def __init__(self, Model, user):
        self.Model = Model
        self.user = user

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
        return data
