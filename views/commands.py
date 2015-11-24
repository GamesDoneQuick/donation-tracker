from tracker.models import *

__all__ = [
    'MoveSpeedRun',
]


def MoveSpeedRun(data):
    moving = SpeedRun.objects.get(pk=data['moving'])
    other = SpeedRun.objects.get(pk=data['other'])
    before = bool(data['before'])
    if moving.order is None:
        if before:
            runs = SpeedRun.objects.filter(event=moving.event, order__gte=other.order)
            final = other.order
        else:
            runs = SpeedRun.objects.filter(event=moving.event, order__gt=other.order)
            final = other.order + 1
        runs = runs.reverse()  # otherwise fixing the order goes in the wrong direction
        first = final
        diff = 1
    elif moving.order < other.order:
        if before:
            runs = SpeedRun.objects.filter(event=moving.event, order__gt=moving.order, order__lt=other.order)
            final = other.order - 1
        else:
            runs = SpeedRun.objects.filter(event=moving.event, order__gt=moving.order, order__lte=other.order)
            final = other.order
        first = moving.order
        diff = -1
    else:  # moving.order > other.order
        if before:
            runs = SpeedRun.objects.filter(event=moving.event, order__gte=other.order, order__lt=moving.order)
            final = other.order
        else:
            runs = SpeedRun.objects.filter(event=moving.event, order__gt=other.order, order__lt=moving.order)
            final = other.order + 1
        runs = runs.reverse()  # otherwise fixing the order goes in the wrong direction
        first = final
        diff = 1
    moving.order = None
    moving.save(fix_time=False)
    for s in runs:
        s.order += diff
        s.save(fix_time=False)
    moving.order = final
    moving.save(fix_time=False)
    models = SpeedRun.objects.get(event=moving.event, order=first).save()
    return models, 200

MoveSpeedRun.permission = 'tracker.change_speedrun'
