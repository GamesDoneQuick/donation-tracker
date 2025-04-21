import React from 'react';
import cn from 'classnames';

import { DonationPostBid, findBidInTree, TreeBid } from '@public/apiv2/APITypes';
import { useCachedCallback } from '@public/hooks/useCachedCallback';
import { useEventCurrency } from '@public/util/currency';
import Button from '@uikit/Button';
import Text from '@uikit/Text';

import { DonationFormEntry } from '@tracker/donation/validateDonation';

import styles from './DonationBids.mod.css';

type BidItemProps = {
  bid: DonationPostBid;
  bids: TreeBid[];
  onDelete: (bid: DonationPostBid) => void;
};

const BidItem = (props: BidItemProps) => {
  const { bid, bids, onDelete } = props;
  const eventCurrency = useEventCurrency();

  const incentive = findBidInTree(bids, 'id' in bid ? bid.id : bid.parent)!;

  const handleDelete = useCachedCallback((bid: DonationPostBid) => onDelete(bid), [onDelete]);

  return (
    <div className={styles.bid}>
      <div className={styles.bidHeader}>
        <div>
          <Text size={Text.Sizes.SIZE_14} marginless>
            Choice: {`${incentive.full_name}${'name' in bid ? ` -- ${bid.name}` : ''}`}
          </Text>
        </div>
        <div>
          <Text className={styles.bidAmount} size={Text.Sizes.SIZE_20} marginless>
            {eventCurrency(bid.amount)}
          </Text>
          <Button
            className={styles.removeButton}
            size={Button.Sizes.SMALL}
            onClick={handleDelete(bid)}
            data-testid={`donationbid-remove-${'id' in bid ? bid.id : `${bid.parent}-custom`}`}>
            Remove Bid
          </Button>
        </div>
      </div>
    </div>
  );
};

type DonationBidsProps = {
  bids: TreeBid[];
  className?: cn.Argument;
  donation: DonationFormEntry;
  deleteBid: (bid: DonationPostBid) => void;
};

const DonationBids = (props: DonationBidsProps) => {
  const { bids, className, donation, deleteBid } = props;

  return bids.length > 0 ? (
    <div className={cn(styles.container, className)}>
      {donation.bids.map((bid, i) => (
        <BidItem key={i} bid={bid} bids={bids} onDelete={deleteBid} />
      ))}
    </div>
  ) : (
    <></>
  );
};

export default DonationBids;
