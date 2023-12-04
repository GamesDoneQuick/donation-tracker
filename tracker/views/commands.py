import json

from django.core.exceptions import ValidationError
from django.db import transaction

from tracker.models import SpeedRun

__all__ = [
    'MoveSpeedRun',
]


def MoveSpeedRun(data):
    moving = SpeedRun.objects.get(pk=data['moving'])
    other = SpeedRun.objects.get(pk=data['other'])
    if moving.event_id != other.event_id:
        return json.dumps({'error': 'Runs are not in the same event'}), 400
    before = bool(data['before'])
    try:
        with transaction.atomic():
            if moving.order is None:
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
            first_run = SpeedRun.objects.get(event=moving.event, order=first)
            first_run.clean()
            models = first_run.save()
            return models, 200
    except ValidationError as e:
        if hasattr(e, 'error_dict'):
            return json.dumps({'error': e.message_dict}), 400
        else:
            return json.dumps({'error': e.messages}), 400


MoveSpeedRun.permission = 'tracker.change_speedrun'
