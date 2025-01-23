from django.core.exceptions import ValidationError

__all__ = [
    'positive',
    'nonzero',
]


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
