import datetime
import math

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.decorators import method_decorator
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
from tracker.api.views.decorators import cache_page_for_public
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

    @method_decorator(cache_page_for_public(60))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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
            if other.anchor_time:
                raise ValidationError(
                    {key: messages.ANCHORED_RUN_BEFORE},
                    code=messages.ANCHORED_RUN_BEFORE_CODE,
                )
            elif moving.order and moving.order < other.order:
                order = other.order - 1
            else:
                order = other.order
        elif key == 'after':
            if (
                queryset.filter(order=other.order + 1)
                .exclude(anchor_time=None)
                .exists()
            ):
                raise ValidationError(
                    {key: messages.ANCHORED_RUN_BEFORE},
                    code=messages.ANCHORED_RUN_BEFORE_CODE,
                )
            elif moving.order and moving.order < other.order:
                order = other.order
            else:
                order = other.order + 1
        elif key == 'order':
            order = self.request.data['order']
            last_order = (
                slot.order + 1
                if (slot := queryset.exclude(order=None).exclude(id=moving.id).last())
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

        if order == moving.order or other == moving:
            raise ValidationError(
                {key: messages.NO_CHANGES}, code=messages.NO_CHANGES_CODE
            )

        try:
            with transaction.atomic():
                # pessimistic, but this endpoint should not get hit very often, so it's probably ok
                # need to actually evaluate it, or it won't lock the rows
                if not queryset.select_for_update().count():
                    raise ValidationError('nonsense')

                # - every run within the range will have its order field changed
                # - if we cross an anchor boundary, every run between the new position and the next anchor
                #   (or the end of the event) will adjust its time, and any flex blocks need to be
                #   recalculated
                # - if we cross an anchor boundary going forwards, and every run between the old position
                #   and the crossed anchor will also adjust
                # - if we cross an anchor boundary going backwards, every run between the old end point
                #   and the next anchor (or the end of the event) will also adjust its time
                # - edge case: moving a flex block needs to ensure the new flex blocks get adjusted
                checkpoints = set()

                time_diff = datetime.timedelta(milliseconds=moving.total_time_ms)

                if moving.order is None:  # adding an unordered run
                    reordered_runs = forward_runs = queryset.filter(order__gte=order)
                    order_diff = 1
                    if first_anchor := next(
                        (r for r in reordered_runs if r.anchor_time is not None), None
                    ):
                        forward_runs = queryset.filter(
                            order__gte=order, order__lt=first_anchor.order
                        )
                        checkpoints.add(forward_runs.last())
                    if slot := reordered_runs.first():
                        moving.starttime = slot.starttime
                    elif slot := queryset.last():  # end of the event
                        moving.starttime = slot.endtime
                    else:
                        moving.starttime = moving.event.datetime
                    backward_runs = queryset.none()
                elif order is None:  # removing an ordered run
                    reordered_runs = backward_runs = queryset.filter(
                        order__gt=moving.order
                    )
                    order_diff = -1
                    if first_anchor := next(
                        (r for r in reordered_runs if r.anchor_time is not None), None
                    ):
                        # see edge case comment above
                        if first_anchor.order == moving.order + 1:
                            checkpoints.add(
                                queryset.filter(order=moving.order - 1).first()
                            )
                        else:
                            backward_runs = queryset.filter(
                                order__gt=moving.order, order__lt=first_anchor.order
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
                        # see edge case comment above
                        if first_anchor.order == moving.order + 1:
                            backward_runs = queryset.none()
                            checkpoints.add(
                                queryset.filter(order=moving.order - 1).first()
                            )
                        else:
                            backward_runs = queryset.filter(
                                order__gt=moving.order, order__lt=first_anchor.order
                            )
                            checkpoints.add(backward_runs.last())
                        forward_runs = queryset.filter(order__gt=order)
                        if next_anchor := forward_runs.exclude(
                            anchor_time=None
                        ).first():
                            forward_runs = forward_runs.filter(
                                order__lt=next_anchor.order
                            )
                            checkpoints.add(forward_runs.last())
                    else:
                        backward_runs = reordered_runs
                        forward_runs = queryset.none()
                    moving.starttime = reordered_runs.last().endtime
                    # if we didn't cross an anchor boundary the moving run needs to be offset by the hole
                    #  it's leaving behind
                    if first_anchor is None:
                        moving.starttime -= time_diff
                else:  # moving.order > order, moving a run backward
                    reordered_runs = queryset.filter(
                        order__gte=order, order__lt=moving.order
                    )
                    order_diff = 1
                    forward_runs = reordered_runs
                    # different edge case here: if a flex block is moved backward, need to explicitly mark the
                    #  preceding run as a flex block, even though the anchor doesn't otherwise change
                    if (
                        queryset.filter(order=moving.order + 1)
                        .exclude(anchor_time=None)
                        .exists()
                    ):
                        checkpoints.add(forward_runs.last())
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
                    moving.starttime = reordered_runs.first().starttime
                changed = (
                    set(reordered_runs)
                    | set(forward_runs)
                    | set(backward_runs)
                    | set((c for c in checkpoints if c is not None))
                )
                changed.add(moving)
                # ensure we're working with the object from the set and not a copy
                moving = next(r for r in changed if r.id == moving.id)
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

                interstitials = Interstitial.objects.filter(
                    anchor__in=changed
                ).select_related('anchor')
                interstitials.update(order=None)
                for i in interstitials:
                    try:
                        i.full_clean(exclude=['order'])
                    except DjangoValidationError as exc:
                        raise DjangoValidationError({'interstitial': exc.messages})
                # have to run it separately -after- we have ensured no other collisions
                for i in interstitials:
                    i.order = i.anchor.order
                Interstitial.objects.bulk_update(interstitials, ['order'])

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
