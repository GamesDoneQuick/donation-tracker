import React from 'react';
import cn from 'classnames';
import { DateTime, Duration } from 'luxon';
import { ConnectDragSource, useDrag, useDrop } from 'react-dnd';

import { ActiveInput } from '@common/ActiveInput';
import { useConstants } from '@common/Constants';
import APIErrorList from '@public/APIErrorList';
import { RunPatch } from '@public/apiv2/APITypes';
import { durationPattern, toInputTime } from '@public/apiv2/helpers/luxon';
import { useLockedPermission, useMoveRunMutation, usePatchRunMutation, usePermission } from '@public/apiv2/hooks';
import { Run } from '@public/apiv2/Models';
import Spinner from '@public/spinner';
import { forceArray } from '@public/util/Types';

import { DragItem } from './dragDrop/dragItem';
import TalentLinks from './TalentLinks';

import styles from './styles.mod.css';

function DragControls({
  drag,
  loading,
  run,
  moveRun,
}: {
  drag: ConnectDragSource;
  loading: boolean;
  run: Run;
  moveRun: (order: number | null) => ReturnType<ReturnType<typeof useMoveRunMutation>[0]>;
}) {
  const saveOrder = React.useCallback((s: string) => moveRun(+s).unwrap(), [moveRun]);

  // possible FIXME for an edge case, if we're the first run, and the second run is anchored, trying
  //  to move or remove ourselves from the order will cause a validation error serverside, so maybe
  //  hide the controls in that case
  // in practice it doesn't seem likely that this an event gets set up this way, and the server rejects
  //  the operation, so maybe it's fine

  return run.anchor_time ? (
    <>{run.order}</>
  ) : (
    <ActiveInput
      className={cn(styles.controls)}
      input={{ style: { maxWidth: 50 }, required: true, min: 1, step: 1, type: 'number' }}
      displayValue={run.order || '-'}
      initialValue={run.order || 1}
      canEdit={true}
      loading={loading}
      confirm={saveOrder}>
      <button
        ref={drag}
        data-testid="drag-handle"
        style={{ cursor: 'grab' }}
        disabled={loading}
        className={cn({ disabled: loading }, 'btn', 'btn-xs', 'fa', 'fa-arrows-v')}
      />
      {run.order != null && (
        <button
          data-testid="unorder-run"
          style={{ cursor: 's-resize' }}
          disabled={loading}
          className={cn({ disabled: loading }, 'btn', 'btn-xs', 'fa', 'fa-times')}
          onClick={() => moveRun(null)}
        />
      )}
    </ActiveInput>
  );
}

function DurationControls({
  patch,
  loading,
  value,
}: {
  patch: (value: string) => Promise<Run>;
  loading: boolean;
  value: Duration;
}) {
  const canChangeRuns = useLockedPermission('tracker.change_speedrun');
  return (
    <ActiveInput
      className={cn(styles.controls)}
      input={{ required: true, pattern: durationPattern.toString().slice(1, -1) }}
      initialValue={value.toFormat('h:mm:ss')}
      canEdit={canChangeRuns}
      loading={loading}
      confirm={patch}
    />
  );
}

function StartTimeControls({
  run: { anchor_time, order, starttime },
  loading,
  patchTime,
}: {
  run: Run;
  loading: boolean;
  patchTime: (value: string | null) => Promise<Run>;
}) {
  const toggleAnchor = React.useCallback(() => {
    if (anchor_time) {
      patchTime(null).catch(() => {});
    } else if (starttime) {
      patchTime(starttime.toISO()).catch(() => {});
    }
  }, [anchor_time, patchTime, starttime]);
  const confirmTime = React.useCallback((value: string) => patchTime(DateTime.fromISO(value).toISO()), [patchTime]);
  const canEditRuns = useLockedPermission('tracker.change_speedrun');

  return (
    <ActiveInput
      className={cn(styles.controls)}
      input={{ type: 'datetime-local' }}
      displayValue={starttime?.toLocaleString(DateTime.DATETIME_MED_WITH_WEEKDAY) || '-'}
      initialValue={anchor_time ? toInputTime(anchor_time) : ''}
      canEdit={canEditRuns && anchor_time != null}
      loading={loading}
      confirm={confirmTime}>
      {starttime && order !== 1 && (
        <button
          disabled={!canEditRuns}
          style={{ opacity: anchor_time ? 1 : 0.5 }}
          className={cn('btn', 'btn-xs', 'fa', 'fa-anchor')}
          data-testid="toggle-anchor"
          onClick={toggleAnchor}
        />
      )}
    </ActiveInput>
  );
}

export function RunRow({ run }: { run: Run }) {
  const { ADMIN_ROOT } = useConstants();
  const canViewRuns = usePermission('tracker.view_speedrun');
  const canChangeRuns = useLockedPermission('tracker.change_speedrun');
  // a run moving between ordered and unordered or vice versa ends up remounting the component, so fixedCacheKey is used
  //  here to preserve the mutation state
  const [moveRun, moveResult] = useMoveRunMutation({ fixedCacheKey: run.id.toString() });
  const [patchRun, patchResult] = usePatchRunMutation();
  const errors = React.useMemo(() => forceArray([moveResult.error, patchResult.error]), [moveResult, patchResult]);
  const colSpan = canViewRuns ? 8 : 7;

  const [{ isDragging, canDrag }, drag, dragPreview] = useDrag<
    DragItem,
    void,
    { isDragging: boolean; canDrag: boolean }
  >(
    () => ({
      type: 'speedrun',
      canDrag: () => !moveResult.isLoading,
      item: () => ({
        id: run.id,
        order: run.order,
      }),
      collect: monitor => ({
        canDrag: !moveResult.isLoading && run.run_time.plus(run.setup_time).toMillis() > 0,
        isDragging: monitor.isDragging(),
      }),
    }),
    [moveResult, run],
  );
  const [{ canDrop, isOver, isItemDragging }, drop] = useDrop<
    DragItem,
    void,
    { isOver: boolean; isItemDragging: boolean; canDrop: boolean }
  >(
    () => ({
      accept: 'speedrun',
      canDrop: item => {
        return (
          item.id !== run.id &&
          run.order != null &&
          (item.order == null || item.order !== run.order - 1) &&
          run.anchor_time == null
        );
      },
      drop(item) {
        moveRun({ id: item.id, before: run.id });
      },
      collect: monitor => {
        return {
          canDrop: monitor.canDrop(),
          isItemDragging: run.order != null && monitor.getItem() != null && monitor.getItem().id !== run.id,
          isOver: monitor.isOver(),
        };
      },
    }),
    [moveRun, run],
  );

  const moveRunTo = React.useCallback((order: number | null) => moveRun({ id: run.id, order }), [moveRun, run.id]);

  const patchField = React.useCallback(
    (field: keyof RunPatch) => (value: string | null) => patchRun({ id: run.id, [field]: value }).unwrap(),
    [patchRun, run.id],
  );

  const resetErrors = React.useCallback(() => {
    moveResult.reset();
    patchResult.reset();
  }, [moveResult, patchResult]);

  return (
    <>
      {errors.length !== 0 && (
        <tr>
          <td colSpan={colSpan}>
            <APIErrorList canHide reset={resetErrors} errors={errors} />
          </td>
        </tr>
      )}
      <tr
        ref={drop}
        data-testid={`run-${run.id}`}
        className={cn(styles.row, {
          [styles.canDrop]: canDrop,
          [styles.isOver]: isOver,
          [styles.isItemDragging]: isItemDragging,
          [styles.isDragging]: isDragging,
        })}>
        <td data-testid="start-time">
          <StartTimeControls run={run} loading={patchResult.isLoading} patchTime={patchField('anchor_time')} />
        </td>
        <td>
          {canChangeRuns && canDrag ? (
            <DragControls drag={drag} loading={moveResult.isLoading} run={run} moveRun={moveRunTo} />
          ) : (
            <Spinner spinning={moveResult.isLoading}>{run.order || '-'}</Spinner>
          )}
        </td>
        <td ref={dragPreview}>{run.name}</td>
        <td>{run.category}</td>
        <td>
          <TalentLinks talent={run.runners} />
        </td>
        <td data-testid="run-time">
          <DurationControls patch={patchField('run_time')} loading={patchResult.isLoading} value={run.run_time} />
        </td>
        <td data-testid="setup-time">
          <DurationControls patch={patchField('setup_time')} loading={patchResult.isLoading} value={run.setup_time} />
        </td>
        {canViewRuns && (
          <td>
            <a href={`${ADMIN_ROOT}speedrun/${run.id}/`}>
              <span className={cn('fa', 'fa-external-link')} aria-hidden={true} />
            </a>
          </td>
        )}
      </tr>
    </>
  );
}
