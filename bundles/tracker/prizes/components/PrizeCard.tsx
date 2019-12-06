import * as React from 'react';
import classNames from 'classnames';
import { useSelector } from 'react-redux';
import _ from 'lodash';

import * as CurrencyUtils from '../../../public/util/currency';
import TimeUtils from '../../../public/util/TimeUtils';
import Button from '../../../uikit/Button';
import Clickable from '../../../uikit/Clickable';
import Header from '../../../uikit/Header';
import Text from '../../../uikit/Text';
import { StoreState } from '../../Store';
import RouterUtils, { Routes } from '../../router/RouterUtils';
import * as PrizeStore from '../PrizeStore';
import { Prize } from '../PrizeTypes';
import PrizeRelativeAvailability from './PrizeRelativeAvailability';

import styles from './PrizeCard.mod.css';

type PrizeCardProps = {
  prizeId: string;
  className?: string;
};

const PrizeCard = (props: PrizeCardProps) => {
  const { prizeId, className } = props;
  const now = TimeUtils.getNowLocal();

  const prize = useSelector((state: StoreState) => PrizeStore.getPrize(state, { prizeId }));

  const handleViewPrize = (prize: Prize) => {
    RouterUtils.navigateTo(Routes.EVENT_PRIZE(prize.eventId, prizeId));
  };

  if (prize == null) {
    return <div className={styles.card} />;
  }

  const prizeImage = _.find([prize.imageFile, prize.image, prize.altImage]);

  return (
    <div className={classNames(styles.card, className)}>
      <Clickable className={styles.imageWrap} onClick={() => handleViewPrize(prize)}>
        <img className={styles.coverImage} src={prizeImage} />
        <Button className={styles.viewDetailsButton} tabIndex={-1}>
          View Details
        </Button>
      </Clickable>
      <div className={styles.content}>
        <Header className={styles.prizeName} size={Header.Sizes.H5}>
          {prize.public}
        </Header>
        <Text size={Text.Sizes.SIZE_14} marginless>
          <PrizeRelativeAvailability prize={prize} now={now} />
        </Text>
      </div>
      <div className={styles.bottomText}>
        <Text className={styles.providedBy} color={Text.Colors.MUTED} size={Text.Sizes.SIZE_12} marginless>
          Provided by
          <br />
          <strong>{prize.provider}</strong>
        </Text>
        <Text className={styles.minimumDonation} color={Text.Colors.MUTED} size={Text.Sizes.SIZE_12} marginless>
          <strong>{CurrencyUtils.asCurrency(prize.minimumBid)}</strong>
          <br />
          {prize.sumDonations ? 'Total Donations' : 'Minimum Donation'}
        </Text>
      </div>
    </div>
  );
};

export default PrizeCard;
