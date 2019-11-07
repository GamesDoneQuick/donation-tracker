import * as React from 'react';
import classNames from 'classnames';
import { useSelector } from 'react-redux';

import useDispatch from '../../hooks/useDispatch';
import * as CurrencyUtils from '../../../public/util/currency';
import { StoreState } from '../../Store';
import Clickable from '../../../uikit/Clickable';
import Header from '../../../uikit/Header';
import Text from '../../../uikit/Text';
import * as IncentiveActions from '../IncentiveActions';
import * as IncentiveStore from '../IncentiveStore';
import { Bid, Incentive } from '../IncentiveTypes';

import styles from './IncentiveBids.mod.css';

type BidItemProps = {
  bid: Bid;
  incentive: Incentive;
  className?: string;
  onDelete: () => void;
};

const BidItem = (props: BidItemProps) => {
  const { bid, incentive, onDelete, className } = props;

  const bidAmount = CurrencyUtils.asCurrency(bid.amount);

  return (
    <Clickable key={incentive.id} className={className} onClick={onDelete}>
      <Header size={Header.Sizes.H4} marginless>
        {incentive.runname}
      </Header>
      <Text size={Text.Sizes.SIZE_14}>{incentive.parent ? incentive.parent.name : incentive.name}</Text>
      <Text size={Text.Sizes.SIZE_14} marginless>
        Choice: {bid.customoptionname || incentive.name}
      </Text>
      <Text size={Text.Sizes.SIZE_14} marginless>
        Amount: {bidAmount}
      </Text>
    </Clickable>
  );
};

type IncentiveBidsProps = {
  className?: string;
};

const IncentiveBids = (props: IncentiveBidsProps) => {
  const { className } = props;

  const dispatch = useDispatch();
  const { bids, incentives } = useSelector((state: StoreState) => ({
    bids: IncentiveStore.getBids(state),
    incentives: IncentiveStore.getIncentivesById(state),
  }));

  const handleDeleteBid = React.useCallback(
    incentiveId => {
      dispatch(IncentiveActions.deleteBid(incentiveId));
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
            className={styles.incentive}
            onDelete={() => handleDeleteBid(bid.incentiveId)}
          />
        );
      })}
    </div>
  );
};

export default IncentiveBids;
