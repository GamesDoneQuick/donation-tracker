from django.core.exceptions import ValidationError
from django.db import transaction

from tracker.models import SpeedRun
from tracker.util import set_mismatch

__all__ = [
    'MoveSpeedRun',
]


def MoveSpeedRun(data):
    try:
        expected_keys = {'moving', 'other', 'before'}
        missing_keys, extra_keys = set_mismatch(expected_keys, data.keys())
        if missing_keys or extra_keys:
            error = ValidationError(
                'required keys were missing and/or extra keys were provided'
            )
            if missing_keys:
                error.error_dict = error.update_error_dict(
                    {'missing_keys': missing_keys}
                )
            if extra_keys:
                error.error_dict = error.update_error_dict({'extra_keys': extra_keys})
            raise error
        moving = SpeedRun.objects.filter(pk=data['moving'], event__locked=False).first()
        other = (
            SpeedRun.objects.filter(pk=data['other'], event__locked=False).first()
            if data.get('other', None)
            else None
        )
        if moving is None:
            raise ValidationError('moving run does not exist or is locked')
        if data['other'] is not None and other is None:
            raise ValidationError('other run does not exist or is locked')
        if moving == other:
            raise ValidationError('runs are the same run')
        if other and moving.event_id != other.event_id:
            raise ValidationError('runs are not from the same event')
        before = bool(data['before'])
        with transaction.atomic():
            if other is None:
                if moving.order is None:
                    raise ValidationError('run is already unordered')
                else:
                    runs = SpeedRun.objects.filter(
                        event=moving.event, order__gt=moving.order
                    ).select_for_update()
                    final = None
                first = moving.order
                diff = -1
            elif moving.order is None:
                if before:
                    runs = SpeedRun.objects.filter(
                        event=moving.event, order__gte=other.order
                    ).select_for_update()
                    final = other.order
                else:
                    runs = SpeedRun.objects.filter(
                        event=moving.event, order__gt=other.order
                    ).select_for_update()
                    final = other.order + 1
                runs = (
                    runs.reverse()
                )  # otherwise fixing the order goes in the wrong direction
                first = final
                diff = 1
            elif moving.order < other.order:
                if before:
                    runs = SpeedRun.objects.filter(
                        event=moving.event,
                        order__gt=moving.order,
                        order__lt=other.order,
                    ).select_for_update()
                    final = other.order - 1
                else:
                    runs = SpeedRun.objects.filter(
                        event=moving.event,
                        order__gt=moving.order,
                        order__lte=other.order,
                    ).select_for_update()
                    final = other.order
                first = moving.order
                diff = -1
            else:  # moving.order > other.order
                if before:
                    runs = SpeedRun.objects.filter(
                        event=moving.event,
                        order__gte=other.order,
                        order__lt=moving.order,
                    ).select_for_update()
                    final = other.order
                else:
                    runs = SpeedRun.objects.filter(
                        event=moving.event,
                        order__gt=other.order,
                        order__lt=moving.order,
                    ).select_for_update()
                    final = other.order + 1
                runs = (
                    runs.reverse()
                )  # otherwise fixing the order goes in the wrong direction
                first = final
                diff = 1
            moving.order = None
            moving.save(fix_time=False)
            for s in runs:
                s.order += diff
                s.save(fix_time=False)
            moving.order = final
            moving.save(fix_time=False)
            first_run = SpeedRun.objects.filter(
                event=moving.event, order__gte=first
            ).first()
            if first_run:
                first_run.clean()
                models = first_run.save()
            else:
                models = []
            # FIXME: horrible order hack until holes can be prevented
            for order, run in enumerate(
                SpeedRun.objects.filter(event=moving.event).exclude(order=None), start=1
            ):
                if run.order != order:
                    run.order = order
                    run.save(fix_time=False)
            if other is None:
                models = models + [moving]
            return models, 200
    except ValidationError as e:
        result = {}
        if hasattr(e, 'error_dict'):
            result.update({'error': e.message_dict})
        elif len(e.messages) > 1:
            result.update({'error': e.messages})
        else:
            result.update({'error': e.message})
        if getattr(e, 'code', None) is not None:
            result['code'] = e.code

        return result, 400


MoveSpeedRun.permission = 'tracker.change_speedrun'
