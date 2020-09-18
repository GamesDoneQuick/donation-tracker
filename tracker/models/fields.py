import re

from django.core import validators
from django.core.exceptions import ValidationError
from django.db import models

# This addresses an unexpected issue where accessing a null OneToOneField from its non-defined side
# will throw an error instead of returning null. There seems to be a 7-year long discussion about
# this, so its likely not going to be resolved (especially since its a fairly big backwards compatiblity break)
# This just modifies the access so that it works the way you think it would
# http://stackoverflow.com/questions/3955093/django-return-none-from-onetoonefield-if-related-object-doesnt-exist


class SingleRelatedObjectDescriptorReturnsNone(
    models.fields.related.ReverseOneToOneDescriptor
):
    def __get__(self, *args, **kwargs):
        try:
            return super(SingleRelatedObjectDescriptorReturnsNone, self).__get__(
                *args, **kwargs
            )
        except models.ObjectDoesNotExist:
            return None


class OneToOneOrNoneField(models.OneToOneField):
    """A OneToOneField that returns None if the related object doesn't exist"""

    related_accessor_class = SingleRelatedObjectDescriptorReturnsNone


class TimestampValidator(validators.RegexValidator):
    regex = r'(?:(?:(\d+):)?(?:(\d+):))?(\d+)(?:\.(\d{1,3}))?$'

    def __call__(self, value):
        super(TimestampValidator, self).__call__(value)
        h, m, s, ms = re.match(self.regex, str(value)).groups()
        if h is not None and int(m) >= 60:
            raise ValidationError(
                'Minutes cannot be 60 or higher if the hour part is specified'
            )
        if m is not None and int(s) >= 60:
            raise ValidationError(
                'Seconds cannot be 60 or higher if the minute part is specified'
            )


class TimestampField(models.Field):
    default_validators = [TimestampValidator()]
    match_string = re.compile(r'(?:(?:(\d+):)?(?:(\d+):))?(\d+)(?:\.(\d+))?')

    def __init__(
        self,
        always_show_h=False,
        always_show_m=False,
        always_show_ms=False,
        *args,
        **kwargs,
    ):
        super(TimestampField, self).__init__(*args, **kwargs)
        self.always_show_h = always_show_h
        self.always_show_m = always_show_m
        self.always_show_ms = always_show_ms

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def to_python(self, value):
        if isinstance(value, str):
            try:
                value = TimestampField.time_string_to_int(value)
            except ValueError:
                return value
        if not value:
            return '0'
        h, m, s, ms = (
            value / 3600000,
            value / 60000 % 60,
            value / 1000 % 60,
            value % 1000,
        )
        if h or self.always_show_h:
            if ms or self.always_show_ms:
                return '%d:%02d:%02d.%03d' % (h, m, s, ms)
            else:
                return '%d:%02d:%02d' % (h, m, s)
        elif m or self.always_show_m:
            if ms or self.always_show_ms:
                return '%d:%02d.%03d' % (m, s, ms)
            else:
                return '%d:%02d' % (m, s)
        else:
            if ms or self.always_show_ms:
                return '%d.%03d' % (s, ms)
            else:
                return '%d' % s

    @staticmethod
    def time_string_to_int(value):
        try:
            if str(int(value)) == value:
                return int(value) * 1000
        except ValueError:
            pass
        if not isinstance(value, str):
            return value
        if not value:
            return 0
        match = TimestampField.match_string.match(value)
        if not match:
            raise ValueError('Not a valid timestamp: ' + value)
        h, m, s, ms = match.groups()
        s = int(s)
        m = int(m or s / 60)
        s %= 60
        h = int(h or m / 60)
        m %= 60
        ms = int(ms or 0)
        return h * 3600000 + m * 60000 + s * 1000 + ms

    def get_prep_value(self, value):
        return TimestampField.time_string_to_int(value)

    def get_internal_type(self):
        return 'IntegerField'

    def validate(self, value, model_instance):
        super(TimestampField, self).validate(value, model_instance)
        try:
            TimestampField.time_string_to_int(value)
        except ValueError:
            raise ValidationError('Not a valid timestamp')
