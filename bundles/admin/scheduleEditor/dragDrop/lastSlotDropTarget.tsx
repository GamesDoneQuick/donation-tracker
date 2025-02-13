import React from 'react';
import cn from 'classnames';
import { useDrop } from 'react-dnd';

import APIErrorList from '@public/APIErrorList';
import { useEventParam, useSplitRuns } from '@public/apiv2/hooks';
import { useMoveRunMutation, useRunsQuery } from '@public/apiv2/reducers/trackerApi';

import { DragItem } from './dragItem';

import styles from './lastSlotDropTarget.mod.css';

interface EmptyTableDropTargetProps {
  elementType: React.ElementType<React.PropsWithChildren>;
  childElementType: React.ElementType<React.PropsWithChildren>;
}

export default function LastSlotDropTarget({
  elementType: Element,
  childElementType: ChildElement,
  children,
}: React.PropsWithChildren<EmptyTableDropTargetProps>) {
  const eventId = useEventParam();
  const [moveRun, result] = useMoveRunMutation();
  const { data: runs } = useRunsQuery({ urlParams: eventId, queryParams: { all: '' } });
  const [orderedRuns] = useSplitRuns(runs);
  const lastRun = React.useMemo(() => orderedRuns.at(-1), [orderedRuns]);

  const [{ isOver, isItemDragging, canDrop }, drop] = useDrop<
    DragItem,
    void,
    { isOver: boolean; isItemDragging: boolean; canDrop: boolean }
  >(
    () => ({
      accept: 'speedrun',
      canDrop: item => item.id !== lastRun?.id,
      drop(item) {
        moveRun({ id: item.id, order: 'last' });
      },
      collect: monitor => ({
        canDrop: monitor.canDrop(),
        isItemDragging: monitor.getItem() != null,
        isOver: monitor.isOver(),
      }),
    }),
    [lastRun, moveRun],
  );

  return drop(
    <Element
      className={cn({ [styles.canDrop]: canDrop, [styles.isOver]: isOver, [styles.isItemDragging]: isItemDragging })}>
      {result.error && (
        <ChildElement>
          <APIErrorList errors={result.error} />
        </ChildElement>
      )}
      {children}
    </Element>,
  );
}
