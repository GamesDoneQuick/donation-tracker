import babel.localedata
from django.core.exceptions import ValidationError


def positive(value):
    if value < 0:
        raise ValidationError('Value cannot be negative')


def nonzero(value):
    if value == 0:
        raise ValidationError('Value cannot be zero')


# TODO: remove this once the historical migrations are removed
def runners_exists(runners):
    from tracker.models import Talent

    for r in runners.split(','):
        try:
            Talent.objects.get_by_natural_key(r.strip())
        except Talent.DoesNotExist:
            raise ValidationError('Runner not found: "%s"' % r.strip())


def validate_locale(name: str):
    name = name.strip()
    if name:
        name = babel.localedata.normalize_locale(name.replace('-', '_')) or name
        if not babel.localedata.exists(name):
            raise ValidationError(f'Unknown locale `{name}`')
