"""Define serialization of the Django models into the REST framework."""

import logging

from rest_framework import serializers

from tracker.models.event import Event, Runner, SpeedRun

log = logging.getLogger(__name__)


class ClassNameField(serializers.Field):
    """Provide the class name as a lowercase string, to provide it as an extra field.

    Borrowed from the DRF docs.
    """

    def get_attribute(self, obj):
        # We pass the object instance onto `to_representation`,
        # not just the field attribute.
        return obj

    def to_representation(self, obj):
        """Serialize the object's class name."""
        return obj.__class__.__name__.lower()


class EventSerializer(serializers.ModelSerializer):
    type = ClassNameField()

    class Meta:
        model = Event
        fields = ('type', 'id', 'short', 'name', 'date', 'timezone')


class RunnerSerializer(serializers.ModelSerializer):
    type = ClassNameField()

    class Meta:
        model = Runner
        fields = ('type', 'id', 'name', 'stream', 'twitter', 'youtube')


class SpeedRunSerializer(serializers.ModelSerializer):
    type = ClassNameField()
    event = EventSerializer()
    runners = RunnerSerializer(many=True)

    class Meta:
        model = SpeedRun
        fields = ('type', 'id', 'event', 'name', 'display_name', 'description', 'category', 'console', 'runners',
                  'commentators', 'starttime', 'endtime', 'order', 'run_time')
