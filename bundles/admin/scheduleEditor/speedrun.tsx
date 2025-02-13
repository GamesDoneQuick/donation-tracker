import React from 'react';
import cn from 'classnames';
import { DateTime } from 'luxon';
import { ConnectDragSource, useDrag, useDrop } from 'react-dnd';

import { useConstants } from '@common/Constants';
import { useLockedPermission, usePermission } from '@public/api/helpers/auth';
import APIErrorList from '@public/APIErrorList';
import { Run } from '@public/apiv2/Models';
import { useMoveRunMutation } from '@public/apiv2/reducers/trackerApi';
import Spinner from '@public/spinner';

import { DragItem } from '@admin/scheduleEditor/dragDrop/dragItem';

import styles from './dragDrop/lastSlotDropTarget.mod.css';

function DragControls({
  drag,
  loading,
  run,
  moveRun,
}: {
  drag: ConnectDragSource;
  loading: boolean;
  run: Run;
  moveRun: ReturnType<typeof useMoveRunMutation>[0];
}) {
  const [order, setOrder] = React.useState<number | null>(null);
  return run.anchor_time ? (
    <>⚓</>
  ) : (
    <Spinner spinning={loading}>
      <span ref={drag} style={{ cursor: 'grab' }}>
        ↕
      </span>
      {run.order != null && (
        <span style={{ cursor: 's-resize' }} onClick={() => moveRun({ id: run.id, order: null })}>
          ❌
        </span>
      )}
      {order != null ? (
        <>
          <input
            style={{ maxWidth: 50 }}
            type="number"
            value={order}
            onChange={e => setOrder(+e.currentTarget.value)}
          />
          <span onClick={() => moveRun({ id: run.id, order }).then(() => setOrder(null))}>✅</span>
          <span onClick={() => setOrder(null)}>🚫</span>
        </>
      ) : (
        <>
          <span onClick={() => setOrder(run.order || 0)}>✏️</span>
          <span>{run.order || '-'}</span>
        </>
      )}
    </Spinner>
  );
}

export function Speedrun({ run }: { run: Run }) {
  const { ADMIN_ROOT } = useConstants();
  const canViewRuns = usePermission('tracker.view_speedrun');
  const canChangeRuns = useLockedPermission('tracker.change_speedrun');
  const canViewTalent = usePermission('tracker.view_talent');
  const [moveRun, moveResult] = useMoveRunMutation({ fixedCacheKey: run.id.toString() });
  const [{ isDragging }, drag, dragPreview] = useDrag<DragItem, void, { isDragging: boolean }>(
    () => ({
      type: 'speedrun',
      canDrag: !moveResult.isLoading,
      item: () => ({
        id: run.id,
        order: run.order,
      }),
      collect: monitor => ({
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
      collect: monitor => ({
        canDrop: monitor.canDrop(),
        isItemDragging: run.order != null && monitor.getItem() != null && monitor.getItem().id !== run.id,
        isOver: monitor.isOver(),
      }),
    }),
    [moveRun, run],
  );
  return (
    <>
      {moveResult.error && <APIErrorList errors={moveResult.error} />}
      <tr
        ref={drop}
        className={cn({
          [styles.canDrop]: canDrop,
          [styles.isOver]: isOver,
          [styles.isItemDragging]: isItemDragging,
          [styles.isDragging]: isDragging,
        })}>
        <td>{run.starttime?.toLocaleString(DateTime.DATETIME_MED_WITH_WEEKDAY) || '-'}</td>
        <td className={styles.dragControls}>
          {canChangeRuns && <DragControls drag={drag} loading={moveResult.isLoading} run={run} moveRun={moveRun} />}
        </td>
        <td ref={dragPreview}>{run.name}</td>
        <td>{run.category}</td>
        <td>
          {run.runners.map((r, i) => (
            <span key={r.id}>
              {i > 0 && ', '}
              {canViewTalent ? <a href={`${ADMIN_ROOT}talent/${r.id}`}>{r.name}</a> : r.name}
            </span>
          ))}
        </td>
        <td>{run.run_time.toFormat('h:mm:ss')}</td>
        <td>{run.setup_time.toFormat('h:mm:ss')}</td>
        <td>{canViewRuns && <a href={`${ADMIN_ROOT}speedrun/${run.id}/`}>✏️</a>}</td>
      </tr>
    </>
  );
}
