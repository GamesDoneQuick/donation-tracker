import datetime
import math

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error

from tracker import logutil
from tracker.api import messages
from tracker.api.pagination import TrackerPagination
from tracker.api.permissions import PrivateGenericPermissions, TechNotesPermission
from tracker.api.serializers import SpeedRunSerializer
from tracker.api.views import (
    EventNestedMixin,
    FlatteningViewSetMixin,
    TrackerFullViewSet,
    WithSerializerPermissionsMixin,
)
from tracker.models import Interstitial, SpeedRun


class SpeedRunViewSet(
    FlatteningViewSetMixin,
    WithSerializerPermissionsMixin,
    EventNestedMixin,
    TrackerFullViewSet,
):
    queryset = SpeedRun.objects.select_related(
        'event', 'priority_tag'
    ).prefetch_related(
        'runners', 'hosts', 'commentators', 'video_links__link_type', 'tags'
    )
    serializer_class = SpeedRunSerializer
    pagination_class = TrackerPagination
    permission_classes = [
        TechNotesPermission,
        *PrivateGenericPermissions('speedrun', lambda r: r.order is not None),
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.detail and 'all' not in self.request.query_params:
            queryset = queryset.exclude(order=None)
        return queryset

    def get_serializer(self, *args, **kwargs):
        with_tech_notes = (
            self.request.method == 'GET' and 'tech_notes' in self.request.query_params
        ) or (
            self.request.method in ('POST', 'PATCH')
            and 'tech_notes' in self.request.data
        )
        return super().get_serializer(*args, with_tech_notes=with_tech_notes, **kwargs)

    def _validate_run_argument(self, data, key, event_id):
        queryset = self.get_queryset()
        if key == 'order':
            if data[key] == 'last':
                return None
            else:
                # might not exist if the order is past the end of the schedule
                try:
                    return queryset.filter(event=event_id, order=data[key]).first()
                except (TypeError, ValueError):
                    raise ValidationError({'order': messages.INVALID_ORDER})
        else:
            try:
                other = queryset.filter(id=data[key]).first()
            except (TypeError, ValueError):
                raise ValidationError({key: messages.INVALID_PK})
        if other is None:
            raise NotFound({key: messages.GENERIC_NOT_FOUND})
        if other.event_id != event_id:
            raise ValidationError(
                {key: messages.SAME_EVENT}, code=messages.SAME_EVENT_CODE
            )
        if other.order is None:
            raise ValidationError(
                {key: messages.UNORDERED_RUN}, code=messages.UNORDERED_RUN_CODE
            )
        return other

    @action(detail=True, methods=['patch'])
    def move(self, *args, **kwargs):
        if len({'before', 'after', 'order'} & self.request.data.keys()) != 1:
            raise ValidationError(
                'provide exactly one of `before`, `after`, or `order`'
            )

        key = next(k for k in {'before', 'after', 'order'} if k in self.request.data)
        moving = self.get_object()
        other = self._validate_run_argument(self.request.data, key, moving.event_id)

        if moving.anchor_time:
            raise ValidationError(
                {key: messages.ANCHORED_RUN_IMMOVABLE},
                code=messages.ANCHORED_RUN_IMMOVABLE_CODE,
            )

        queryset = self.get_queryset().filter(event=moving.event_id)
        if key == 'before':
            if moving.order and moving.order < other.order:
                order = other.order - 1
            else:
                order = other.order
            if other.anchor_time:
                raise ValidationError(
                    {key: messages.ANCHORED_RUN_BEFORE},
                    code=messages.ANCHORED_RUN_BEFORE_CODE,
                )
        elif key == 'after':
            if moving.order is None or moving.order > other.order:
                order = other.order + 1
            else:
                order = other.order
            if (
                queryset.filter(order=other.order + 1)
                .exclude(anchor_time=None)
                .exists()
            ):
                raise ValidationError(
                    {key: messages.ANCHORED_RUN_BEFORE},
                    code=messages.ANCHORED_RUN_BEFORE_CODE,
                )
        elif key == 'order':
            order = self.request.data['order']
            last_order = (
                last.order + 1
                if (last := queryset.exclude(order=None).exclude(id=moving.id).last())
                else 1
            )
            if order == 'last':
                order = last_order
            elif order is not None:
                try:
                    order = min(int(order), last_order)
                except (TypeError, ValueError):
                    order = 0
                if order <= 0:
                    raise ValidationError({key: messages.INVALID_ORDER})
                if other and other.anchor_time:
                    raise ValidationError(
                        {key: messages.ANCHORED_RUN_BEFORE},
                        code=messages.ANCHORED_RUN_BEFORE_CODE,
                    )
        else:
            assert False, 'how did we get here'

        if order == moving.order:
            raise ValidationError(
                {key: messages.NO_CHANGES}, code=messages.NO_CHANGES_CODE
            )

        try:
            with transaction.atomic():
                # pessimistic but this endpoint should not get hit very often

                # queryset.select_for_update()

                # - every run within the range will have its order field changed
                # - if we cross an anchor boundary going forwards, every run between the new end
                #  point and the next anchor (or through the end of the event if there isn't one)
                #  will adjust its time
                # - if we cross an anchor boundary going backwards, every run between the new end point
                #  and the next anchor will also adjust its time
                checkpoints = set()
                if other := queryset.filter(order=order).first():
                    if other.anchor_time:
                        moving.starttime = other.endtime
                    else:
                        moving.starttime = other.starttime
                elif order is not None:
                    if last := queryset.exclude(order=None).last():
                        moving.starttime = last.endtime
                    else:
                        moving.starttime = moving.event.datetime

                time_diff = datetime.timedelta(milliseconds=moving.total_time_ms)

                if moving.order is None:
                    reordered_runs = forward_runs = queryset.filter(order__gte=order)
                    order_diff = 1
                    first_anchor = next(
                        (r for r in reordered_runs if r.anchor_time is not None), None
                    )
                    if first_anchor:
                        forward_runs = queryset.filter(
                            order__gte=order, order__lt=first_anchor.order
                        )
                        checkpoints.add(forward_runs.last())
                    backward_runs = queryset.none()
                elif order is None:
                    reordered_runs = backward_runs = queryset.filter(
                        order__gt=moving.order
                    )
                    order_diff = -1
                    first_anchor = next(
                        (r for r in reordered_runs if r.anchor_time is not None), None
                    )
                    if first_anchor:
                        backward_runs = queryset.filter(
                            order_gt=moving.order, order__lt=first_anchor.order
                        )
                        checkpoints.add(backward_runs.last())
                    forward_runs = queryset.none()
                elif moving.order < order:  # moving a run forward
                    reordered_runs = queryset.filter(
                        order__gt=moving.order, order__lte=order
                    )
                    order_diff = -1
                    if first_anchor := next(
                        (r for r in reordered_runs if r.anchor_time is not None), None
                    ):
                        backward_runs = queryset.filter(
                            order__gt=moving.order, order__lt=first_anchor.order
                        )
                        checkpoints.add(backward_runs.last())
                        forward_runs = queryset.filter(
                            order__gte=order, anchor_time=None
                        )
                        if (
                            next_anchor := queryset.filter(order__gt=order)
                            .exclude(anchor_time=None)
                            .first()
                        ):
                            forward_runs = forward_runs.filter(
                                order__lt=next_anchor.order
                            )
                            checkpoints.add(forward_runs.last())
                    else:
                        backward_runs = reordered_runs
                        forward_runs = queryset.none()
                        # the one case where the run being moved needs further start time adjustment
                        moving.starttime = reordered_runs.last().endtime - time_diff
                else:  # moving.order > order, moving a run backward
                    reordered_runs = queryset.filter(
                        order__gte=order, order__lt=moving.order
                    )
                    order_diff = 1
                    forward_runs = reordered_runs
                    if first_anchor := next(
                        (r for r in reordered_runs if r.anchor_time is not None), None
                    ):
                        forward_runs = reordered_runs.filter(
                            order__lt=first_anchor.order, anchor_time=None
                        )
                        checkpoints.add(forward_runs.last())
                        backward_runs = queryset.filter(order__gt=moving.order)
                        if next_anchor := backward_runs.exclude(
                            anchor_time=None
                        ).first():
                            backward_runs = backward_runs.filter(
                                order__lt=next_anchor.order
                            )
                            checkpoints.add(backward_runs.last())
                    else:
                        backward_runs = queryset.none()
                changed = (
                    set(reordered_runs)
                    | set(forward_runs)
                    | set(backward_runs)
                    | set(checkpoints)
                )
                changed.add(moving)
                # ensure we're working with the object from the set and not a copy
                reordered_runs = {r for r in changed if r in reordered_runs}
                forward_runs = {r for r in changed if r in forward_runs}
                backward_runs = {r for r in changed if r in backward_runs}
                checkpoints = {r for r in changed if r in checkpoints}

                for run in reordered_runs:
                    run.order += order_diff
                for run in backward_runs:
                    run.starttime -= time_diff
                    run.endtime = run.starttime + datetime.timedelta(
                        milliseconds=run.total_time_ms
                    )
                for run in forward_runs:
                    run.starttime += time_diff
                    run.endtime = run.starttime + datetime.timedelta(
                        milliseconds=run.total_time_ms
                    )
                moving.order = order
                if order:
                    moving.endtime = moving.starttime + datetime.timedelta(
                        milliseconds=moving.total_time_ms
                    )
                else:
                    moving.starttime = moving.endtime = None

                # clear out the order field in the DB before rewriting them all, else we get conflicts
                queryset.filter(id__in=(c.id for c in changed)).update(order=None)
                queryset.bulk_update(changed, ['order', 'starttime', 'endtime'])

                for run in checkpoints:
                    # update setup time
                    run.full_clean()
                    run.save()

                for run in changed:
                    run.full_clean()

                # deal with the degenerate case where order gaps occur
                for correct_order, run in enumerate(
                    queryset.exclude(order=None), start=1
                ):
                    if run.order != correct_order:
                        # ensure we have the copy from the set if it exists
                        run = next((r for r in changed if r == run), run)
                        run.order = correct_order
                        run.save()
                        changed.add(run)

                interstitials = Interstitial.objects.filter(anchor__in=changed)
                for i in interstitials:
                    i.full_clean()
                    i.save()

                logutil.change(self.request, moving, ['order'])
        except DjangoValidationError as exc:
            raise ValidationError(detail=as_serializer_error(exc))

        return Response(
            sorted(
                self.get_serializer(changed, many=True).data,
                # TODO: include ads/interviews
                key=lambda m: (m['type'], m['order'] or math.inf),
            )
        )
