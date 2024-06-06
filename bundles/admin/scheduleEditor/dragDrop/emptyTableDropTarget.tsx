import React from 'react';
import { useDrop } from 'react-dnd';

interface EmptyTableDropTargetProps {
  elementType: React.ElementType;
  children: typeof React.Children;
  moveSpeedrun: (id: number) => void;
}

interface DragItem {
  id: number;
}

export default function EmptyTableDropTarget(props: EmptyTableDropTargetProps) {
  const { elementType: Element, children, moveSpeedrun } = props;

  const [{ isOver, canDrop }, drop] = useDrop<DragItem, unknown, { isOver: boolean; canDrop: boolean }>(() => ({
    accept: ['speedrun'],
    drop(item) {
      moveSpeedrun(item.id);
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
