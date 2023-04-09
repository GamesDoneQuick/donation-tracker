import React from 'react';
import { useDrop } from 'react-dnd';

interface EmptyTableDropTargetProps {
  elementType: React.ElementType;
  children: typeof React.Children;
  moveSpeedrun: (pk: number) => void;
}

interface DragItem {
  pk: number;
}

export default function EmptyTableDropTarget(props: EmptyTableDropTargetProps) {
  const { elementType: Element, children, moveSpeedrun } = props;

  const [{ isOver, canDrop }, drop] = useDrop<DragItem, unknown, { isOver: boolean; canDrop: boolean }>(() => ({
    accept: ['speedrun'],
    drop({ pk }) {
      moveSpeedrun(pk);
    },
    collect: monitor => ({
      canDrop: monitor.canDrop(),
      isOver: monitor.isOver(),
    }),
  }));

  return drop(
    <Element
      style={{
        backgroundColor: isOver && canDrop ? 'green' : 'inherit',
      }}>
      {children}
    </Element>,
  );
}
