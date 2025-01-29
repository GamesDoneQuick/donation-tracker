import * as React from 'react';
import classNames from 'classnames';
import { useDrag, useDrop } from 'react-dnd';
import { Clickable, Stack, Text } from '@spyrothon/sparx';

import type { APIDonation as Donation } from '@public/apiv2/APITypes';
import { DonationBid } from '@public/apiv2/Models';
import * as CurrencyUtils from '@public/util/currency';
import DragHandle from '@uikit/icons/DragHandle';

import HighlightKeywords from './HighlightKeywords';

import styles from './DonationRow.mod.css';

const UNKNOWN_DONOR_NAME = '(unknown)';

interface BidsRowProps {
  bids: DonationBid[];
  currency: string;
}

function BidsRow(props: BidsRowProps) {
  const { bids, currency } = props;
  if (bids.length === 0) return null;

  const bidNames = bids.map(bid => `${bid.bid_name} (${CurrencyUtils.asCurrency(bid.amount, { currency })})`);

  return (
    <Text variant="text-sm/normal" className={styles.bids}>
      Attached Bids: {bidNames.join(' • ')}
    </Text>
  );
}

function useDonationDragAndDrop(
  donation: Donation,
  onDrop?: (item: Donation) => unknown,
  checkDrop?: (item: Donation) => boolean,
) {
  const rowRef = React.useRef<HTMLDivElement>(null);
  const [{ isDragging }, drag, preview] = useDrag(() => ({
    type: 'donation',
    item: donation,
    collect: monitor => ({ isDragging: monitor.isDragging() }),
  }));
  const [{ isOver, canDrop }, drop] = useDrop(() => ({
    accept: ['donation'],
    drop: onDrop,
    canDrop: checkDrop,
    collect: monitor => ({
      isOver: monitor.isOver(),
      canDrop: monitor.canDrop(),
    }),
  }));
  drop(preview(rowRef.current));

  return [{ isDragging, isOver, canDrop }, rowRef, drag] as const;
}

interface DonationRowProps {
  donation: Donation;
  draggable?: boolean;
  showBids?: boolean;
  getBylineElements: (donation: Donation) => React.ReactNode[];
  renderActions: (donation: Donation) => React.ReactNode;
  onDrop?: (item: Donation) => unknown;
  canDrop?: (item: Donation) => boolean;
}

export default function DonationRow(props: DonationRowProps) {
  const {
    donation,
    draggable = false,
    showBids = false,
    getBylineElements,
    renderActions,
    onDrop,
    canDrop: checkDrop,
  } = props;

  const amount = CurrencyUtils.asCurrency(donation.amount, { currency: donation.currency });
  const donationTitle = (
    <Text variant="header-sm/normal">
      <strong>{amount}</strong>
      <Text tag="span" variant="text-md/secondary">
        {' from '}
      </Text>
      <strong>
        <HighlightKeywords>{donation.donor_name || UNKNOWN_DONOR_NAME}</HighlightKeywords>
      </strong>
      {donation.pinned && '📌'}
    </Text>
  );

  const renderedByline = getBylineElements(donation).map((element, index) => (
    <React.Fragment key={index}>
      {index > 0 ? ' · ' : null}
      {element}
    </React.Fragment>
  ));

  const [{ isDragging, isOver, canDrop }, rowRef, handleRef] = useDonationDragAndDrop(donation, onDrop, checkDrop);
  const dragHandle = draggable ? (
    <Text variant="text-md/normal">
      <Clickable ref={handleRef} className={styles.dragHandle} aria-label="Drag Donation">
        <DragHandle />
      </Clickable>
    </Text>
  ) : null;

  const hasComment = donation.comment != null && donation.comment.length > 0;
  const donationComment = (
    <Text
      variant={hasComment ? 'text-md/normal' : 'text-md/secondary'}
      className={classNames(styles.comment, { [styles.noCommentHint]: !hasComment })}>
      {hasComment ? <HighlightKeywords>{donation.comment || ''}</HighlightKeywords> : <em>No comment was provided</em>}
    </Text>
  );

  return (
    <div
      ref={rowRef}
      data-test-pk={donation.id}
      tabIndex={-1}
      className={classNames(styles.container, {
        [styles.isDropOver]: isOver && canDrop,
        [styles.dragging]: isDragging,
      })}>
      {onDrop != null ? <div className={styles.dropIndicator} /> : null}
      <div className={styles.header}>
        <Stack direction="horizontal" justify="space-between" align="center" className={styles.headerTop}>
          <Stack direction="horizontal" align="center" spacing="space-lg">
            {dragHandle}
            <Stack spacing="space-none">
              {donationTitle}
              <Text variant="text-sm/secondary">{renderedByline}</Text>
            </Stack>
          </Stack>
          {renderActions(donation)}
        </Stack>
        {showBids ? <BidsRow bids={donation.bids} currency={donation.currency} /> : null}
      </div>
      {donationComment}
    </div>
  );
}
