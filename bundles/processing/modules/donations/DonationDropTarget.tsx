import React from 'react';
import cn from 'classnames';
import { useDrop } from 'react-dnd';

import { Donation } from '@public/apiv2/Models';

import styles from './DonationRow.mod.css';

interface DonationDropTargetProps {
  onDrop: (item: Donation) => unknown;
  canDrop: (item: Donation) => boolean;
}

export default function DonationDropTarget(props: DonationDropTargetProps) {
  const { canDrop: canDropPredicate, onDrop } = props;

  const [{ isOver, canDrop }, drop] = useDrop(
    () => ({
      accept: ['donation'],
      drop: onDrop,
      canDrop: canDropPredicate,
      collect(monitor) {
        return {
          isOver: monitor.isOver(),
          canDrop: monitor.canDrop(),
        };
      },
    }),
    [canDropPredicate, onDrop],
  );

  return (
    <div ref={drop} className={cn(styles.emptyDropTarget, { [styles.isDropOver]: isOver && canDrop })}>
      <div className={styles.dropIndicator} />
    </div>
  );
}
