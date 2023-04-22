import * as React from 'react';
import classNames from 'classnames';
import { useDrop } from 'react-dnd';

import type { Donation } from '@public/apiv2/APITypes';

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
    [onDrop],
  );

  return (
    <div ref={drop} className={classNames(styles.emptyDropTarget, { [styles.isDropOver]: isOver && canDrop })}>
      <div className={styles.dropIndicator} />
    </div>
  );
}
