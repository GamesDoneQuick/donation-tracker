import React from 'react';
import { useDrop } from 'react-dnd';

import Constants from '@common/Constants';

interface SpeedrunDropTargetProps {
  before: boolean;
  pk: number;
  moveSpeedrun: (source: number, dest: number, before: boolean) => void;
}

interface DropItem {
  pk: number;
  anchored: boolean;
}

export default function SpeedrunDropTarget(props: SpeedrunDropTargetProps) {
  const { STATIC_URL } = React.useContext(Constants);

  const { before, pk, moveSpeedrun } = props;

  const [{ isOver, canDrop }, drop] = useDrop<DropItem, unknown, { isOver: boolean; canDrop: boolean }>(() => ({
    accept: ['speedrun'],
    drop({ pk: sourcePk }) {
      moveSpeedrun(sourcePk, pk, before);
    },
    canDrop({ pk: sourcePk, anchored }) {
      return pk !== sourcePk && (anchored || !before);
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
