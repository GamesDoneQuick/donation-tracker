import React, { useCallback, useState } from 'react';
import classNames from 'classnames';
import { useSelector } from 'react-redux';
import { useNavigate } from 'react-router';

import * as CurrencyUtils from '@public/util/currency';
import TimeUtils from '@public/util/TimeUtils';
import Button from '@uikit/Button';
import Clickable from '@uikit/Clickable';
import Header from '@uikit/Header';
import Text from '@uikit/Text';

import RouterUtils, { Routes } from '@tracker/router/RouterUtils';
import { StoreState } from '@tracker/Store';

import getPrizeRelativeAvailability from '../getPrizeRelativeAvailability';
import * as PrizeStore from '../PrizeStore';
import * as PrizeUtils from '../PrizeUtils';

import styles from './PrizeCard.mod.css';

type PrizeCardProps = {
  // TODO: should be a number
  prizeId: string;
  currency: string;
  className?: string;
};

const PrizeCard = (props: PrizeCardProps) => {
  const { prizeId, className, currency } = props;
  const now = TimeUtils.getNowLocal();

  const [prizeError, setPrizeError] = useState(false);
  const setPrizeErrorTrue = useCallback(() => setPrizeError(true), []);

  const prize = useSelector((state: StoreState) => PrizeStore.getPrize(state, { prizeId }));

  const navigate = useNavigate();

  const handleViewPrize = useCallback(() => {
    if (prize) {
      RouterUtils.navigateTo(navigate, Routes.EVENT_PRIZE(prize.eventId, prize.id));
    }
  }, [navigate, prize]);

  if (prize == null) {
    return <div className={styles.card} />;
  }

  const coverImage = prizeError ? null : PrizeUtils.getSummaryImage(prize);

  return (
    <Clickable className={classNames(styles.card, className)} onClick={handleViewPrize}>
      <div className={styles.imageWrap}>
        {coverImage != null ? (
          <img alt={prize.public} onError={setPrizeErrorTrue} className={styles.coverImage} src={coverImage} />
        ) : (
          <div className={styles.noCoverImage}>
            <Header size={Header.Sizes.H4} color={Header.Colors.MUTED}>
              No Image Provided
            </Header>
          </div>
        )}
        <Button className={styles.viewDetailsButton} tabIndex={-1}>
          View Details
        </Button>
      </div>
      <div className={styles.content}>
        <Header className={styles.prizeName} size={Header.Sizes.H5}>
          {prize.public}
          {prize.category && ` \u2014 ${prize.category.name}`}
        </Header>
        <Text size={Text.Sizes.SIZE_14} marginless>
          {getPrizeRelativeAvailability(prize, now)}
        </Text>
      </div>
      <div className={styles.bottomText}>
        {prize.provider ? (
          <Text className={styles.providedBy} color={Text.Colors.MUTED} size={Text.Sizes.SIZE_12} marginless>
            Provided by
            <br />
            <strong>{prize.provider}</strong>
          </Text>
        ) : null}
        <Text className={styles.minimumDonation} color={Text.Colors.MUTED} size={Text.Sizes.SIZE_12} marginless>
          <strong>{CurrencyUtils.asCurrency(prize.minimumBid, { currency })}</strong>
          <br />
          {prize.sumDonations ? 'Total Donations' : 'Minimum Donation'}
        </Text>
      </div>
    </Clickable>
  );
};

export default PrizeCard;
