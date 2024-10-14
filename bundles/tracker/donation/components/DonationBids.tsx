import * as React from 'react';
import classNames from 'classnames';
import { useSelector } from 'react-redux';

import { useCachedCallback } from '@public/hooks/useCachedCallback';
import * as CurrencyUtils from '@public/util/currency';
import Button from '@uikit/Button';
import ErrorAlert from '@uikit/ErrorAlert';
import Header from '@uikit/Header';
import Text from '@uikit/Text';

import * as EventDetailsStore from '@tracker/event_details/EventDetailsStore';
import { Incentive } from '@tracker/event_details/EventDetailsTypes';
import useDispatch from '@tracker/hooks/useDispatch';
import { StoreState } from '@tracker/Store';

import * as DonationActions from '../DonationActions';
import * as DonationStore from '../DonationStore';
import { Bid, BidFormErrors } from '../DonationTypes';

import styles from './DonationBids.mod.css';

type BidItemProps = {
  bid: Bid;
  incentive: Incentive;
  onDelete: () => void;
  errors?: BidFormErrors;
};

const BidItem = (props: BidItemProps) => {
  const { bid, incentive, onDelete, errors } = props;
  const currency = useSelector(EventDetailsStore.getEventCurrency);
  const bidAmount = CurrencyUtils.asCurrency(bid.amount, { currency });

  return (
    <div className={styles.bid}>
      <ErrorAlert errors={errors && errors.bid} />
      <ErrorAlert errors={errors && errors.customoptionname} />
      <ErrorAlert errors={errors && errors.amount} />
      <div className={styles.bidHeader}>
        <div>
          <Header size={Header.Sizes.H4} marginless>
            {incentive.runname}
          </Header>
          <Text size={Text.Sizes.SIZE_14}>{incentive.parent ? incentive.parent.name : incentive.name}</Text>
          <Text size={Text.Sizes.SIZE_14} marginless>
            Choice: {bid.customoptionname || incentive.name}
          </Text>
        </div>
        <div>
          <Text className={styles.bidAmount} size={Text.Sizes.SIZE_20} marginless>
            {bidAmount}
          </Text>
          <Button
            className={styles.removeButton}
            size={Button.Sizes.SMALL}
            onClick={onDelete}
            data-testid={`donationbid-remove-${bid.incentiveId}`}>
            Remove Bid
          </Button>
        </div>
      </div>
    </div>
  );
};

type DonationBidsProps = {
  className?: string;
};

const DonationBids = (props: DonationBidsProps) => {
  const { className } = props;

  const dispatch = useDispatch();
  const { bids, incentives, bidErrors } = useSelector((state: StoreState) => ({
    bids: DonationStore.getBids(state),
    incentives: EventDetailsStore.getIncentivesById(state),
    bidErrors: DonationStore.getBidsFormErrors(state),
  }));

  const handleDeleteBid = useCachedCallback(
    incentiveId => {
      dispatch(DonationActions.deleteBid(incentiveId));
    },
    [dispatch],
  );

  return (
    <div className={classNames(styles.container, className)}>
      {bids.map((bid, i) => {
        if (bid.incentiveId) {
          const incentive = incentives[bid.incentiveId];
          return (
            <BidItem
              key={incentive.id}
              bid={bid}
              errors={bidErrors[i]}
              incentive={incentive}
              onDelete={handleDeleteBid(bid.incentiveId)}
            />
          );
        } else {
          return <ErrorAlert key={`missing-${i}`} errors={bidErrors[i].bid} />;
        }
      })}
    </div>
  );
};

export default DonationBids;
