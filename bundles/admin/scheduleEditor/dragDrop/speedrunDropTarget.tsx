import React from 'react';
import { useDrop } from 'react-dnd';

import Constants from '@common/Constants';

interface SpeedrunDropTargetProps {
  before: boolean;
  id: number;
  moveSpeedrun: (source: number, dest: number, before: boolean) => void;
}

interface DropItem {
  id: number;
}

export default function SpeedrunDropTarget(props: SpeedrunDropTargetProps) {
  const { STATIC_URL } = React.useContext(Constants);

  const { before, id, moveSpeedrun } = props;

  const [{ isOver, canDrop }, drop] = useDrop<DropItem, unknown, { isOver: boolean; canDrop: boolean }>(() => ({
    accept: ['speedrun'],
    drop({ id: sourceId }) {
      moveSpeedrun(sourceId, id, before);
    },
    collect: monitor => ({
      canDrop: monitor.canDrop(),
      isOver: monitor.isOver(),
    }),
  }));

  return drop(
    <span
      style={{
        width: '50%',
        backgroundColor: isOver && canDrop ? 'green' : 'inherit',
        float: before ? 'left' : 'right',
      }}>
      <img src={STATIC_URL + (before ? 'prev.png' : 'next.png')} alt={before ? 'previous' : 'next'} />
    </span>,
  );
}
