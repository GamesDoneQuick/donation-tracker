import * as React from 'react';
import classNames from 'classnames';
import { useSelector } from 'react-redux';

import useDispatch from '../../hooks/useDispatch';
import * as CurrencyUtils from '../../../public/util/currency';
import { StoreState } from '../../Store';
import Button from '../../../uikit/Button';
import Header from '../../../uikit/Header';
import Text from '../../../uikit/Text';
import * as EventDetailsStore from '../../event_details/EventDetailsStore';
import { Incentive } from '../../event_details/EventDetailsTypes';
import * as DonationActions from '../DonationActions';
import * as DonationStore from '../DonationStore';
import { Bid } from '../DonationTypes';

import styles from './DonationBids.mod.css';

type BidItemProps = {
  bid: Bid;
  incentive: Incentive;
  onDelete: () => void;
};

const BidItem = (props: BidItemProps) => {
  const { bid, incentive, onDelete } = props;

  const bidAmount = CurrencyUtils.asCurrency(bid.amount);

  return (
    <div className={styles.bid}>
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
          <Button className={styles.removeButton} size={Button.Sizes.SMALL} onClick={onDelete}>
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
  const { bids, incentives } = useSelector((state: StoreState) => ({
    bids: DonationStore.getBids(state),
    incentives: EventDetailsStore.getIncentivesById(state),
  }));

  const handleDeleteBid = React.useCallback(
    incentiveId => {
      dispatch(DonationActions.deleteBid(incentiveId));
    },
    [dispatch],
  );

  return (
    <div className={classNames(styles.container, className)}>
      {bids.map(bid => {
        const incentive = incentives[bid.incentiveId];
        return (
          <BidItem
            key={incentive.id}
            bid={bid}
            incentive={incentive}
            onDelete={() => handleDeleteBid(bid.incentiveId)}
          />
        );
      })}
    </div>
  );
};

export default DonationBids;
