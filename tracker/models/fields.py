import datetime
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


class Duration:
    match_string = re.compile(r'(?:(?:(\d+):)?(?:(\d+):))?(\d+)')

    def __init__(
        self, value=None, always_show_h=False, always_show_m=False,
    ):
        self.always_show_h = always_show_h
        self.always_show_m = always_show_m
        if isinstance(value, str):
            if value == '':
                self.value = datetime.timedelta(seconds=0)
            else:
                match = self.match_string.match(value)
                if not match:
                    raise ValueError('Not a valid timestamp: ' + value)
                h, m, s = match.groups()
                s = int(s)
                m = int(m or s / 60)
                s %= 60
                h = int(h or m / 60)
                m %= 60
                self.value = datetime.timedelta(hours=h, minutes=m, seconds=s)
        elif isinstance(value, (int, float)):
            self.value = datetime.timedelta(seconds=int(value))
        elif isinstance(value, Duration):
            self.value = datetime.timedelta(seconds=value.value.seconds)
        elif isinstance(value, datetime.timedelta):
            self.value = datetime.timedelta(seconds=value.seconds)
        elif value is None:
            self.value = datetime.timedelta(seconds=0)
        else:
            raise ValueError(f'Unsupported input to Duration: {value!r}')

    def __bool__(self):
        return self.value.seconds != 0

    def __eq__(self, other):
        try:
            return self.value == Duration(other).value
        except ValueError:
            return NotImplemented

    def __add__(self, other):
        if isinstance(other, Duration):
            return Duration(
                self.value + other.value,
                always_show_h=self.always_show_h,
                always_show_m=self.always_show_m,
            )
        if isinstance(other, datetime.timedelta):
            return Duration(
                self.value + other,
                always_show_h=self.always_show_h,
                always_show_m=self.always_show_m,
            )
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, Duration):
            return Duration(
                self.value - other.value,
                always_show_h=self.always_show_h,
                always_show_m=self.always_show_m,
            )
        if isinstance(other, datetime.timedelta):
            return Duration(
                self.value - other,
                always_show_h=self.always_show_h,
                always_show_m=self.always_show_m,
            )
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, datetime.datetime):
            return other + self.value
        return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, datetime.datetime):
            return other - self.value
        return NotImplemented

    def __str__(self):
        s = self.value.seconds
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        if h or self.always_show_h:
            return '%d:%02d:%02d' % (h, m, s)
        elif m or self.always_show_m:
            return '%d:%02d' % (m, s)
        else:
            return '%d' % s


class TimestampField(models.Field):
    default_validators = [TimestampValidator()]
    match_string = re.compile(r'(?:(?:(\d+):)?(?:(\d+):))?(\d+)(?:\.(\d+))?')

    def __init__(
        self, always_show_h=False, always_show_m=False, *args, **kwargs,
    ):
        super(TimestampField, self).__init__(*args, **kwargs)
        self.always_show_h = always_show_h
        self.always_show_m = always_show_m

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def to_python(self, value):
        return Duration(value, self.always_show_h, self.always_show_m)

    def get_prep_value(self, value):
        return Duration(value).value.seconds

    def get_internal_type(self):
        return 'IntegerField'

    def validate(self, value, model_instance):
        super(TimestampField, self).validate(value, model_instance)
        try:
            Duration(value)
        except ValueError:
            raise ValidationError('Not a valid timestamp')
