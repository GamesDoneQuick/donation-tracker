import React from 'react';
import cn from 'classnames';
import { useNavigate } from 'react-router';

import { useEventFromRoute, useRunsQuery, useSplitRuns } from '@public/apiv2/hooks';
import { Prize } from '@public/apiv2/Models';
import { useBooleanState } from '@public/hooks/useBooleanState';
import { useNow } from '@public/hooks/useNow';
import { useEventCurrency } from '@public/util/currency';
import Button from '@uikit/Button';
import Clickable from '@uikit/Clickable';
import Header from '@uikit/Header';
import Text from '@uikit/Text';

import RouterUtils, { Routes } from '@tracker/router/RouterUtils';

import getPrizeRelativeAvailability from '../getPrizeRelativeAvailability';
import * as PrizeUtils from '../PrizeUtils';

import styles from './PrizeCard.mod.css';

type PrizeCardProps = {
  prize: Prize;
  className?: cn.Argument;
};

const PrizeCard = ({ className, prize }: PrizeCardProps) => {
  const now = useNow();
  const navigate = useNavigate();

  const { id: eventId, path: eventPath } = useEventFromRoute();
  const { data: runs } = useRunsQuery({ urlParams: eventId }, { skip: eventId == null });
  const [orderedRuns] = useSplitRuns(runs);

  const handleViewPrize = React.useCallback(() => {
    if (prize) {
      RouterUtils.navigateTo(navigate, Routes.EVENT_PRIZE(eventPath, prize.id));
    }
  }, [eventPath, navigate, prize]);

  const [imageError, setImageErrorTrue] = useBooleanState();
  const coverImage = imageError ? null : PrizeUtils.getSummaryImage(prize);

  const eventCurrency = useEventCurrency();

  return (
    <Clickable className={cn(styles.card, className)} onClick={handleViewPrize}>
      <div className={styles.imageWrap}>
        {coverImage != null ? (
          <img alt={prize.name} onError={setImageErrorTrue} className={styles.coverImage} src={coverImage} />
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
          {prize.name}
        </Header>
        <Text size={Text.Sizes.SIZE_14} marginless>
          {getPrizeRelativeAvailability(prize, now, orderedRuns)}
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
          <strong>{eventCurrency(prize.minimumbid)}</strong>
          <br />
          {prize.sumdonations ? 'Total Donations' : 'Minimum Donation'}
        </Text>
      </div>
    </Clickable>
  );
};

export default PrizeCard;
