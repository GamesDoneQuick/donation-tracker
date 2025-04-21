import React from 'react';

import { useConstants } from '@common/Constants';
import { useEventFromRoute } from '@public/apiv2/hooks';
import { Prize } from '@public/apiv2/Models';
import * as CurrencyUtils from '@public/util/currency';
import Anchor from '@uikit/Anchor';
import Header from '@uikit/Header';
import LoadingDots from '@uikit/LoadingDots';
import Text from '@uikit/Text';

import { Routes } from '@tracker/router/RouterUtils';

import styles from './DonationPrizes.mod.css';

type PrizeProps = {
  prize: Prize;
};

const PrizeRow = (props: PrizeProps) => {
  const { prize } = props;
  const { data: event, path: eventPath } = useEventFromRoute();

  return event ? (
    <div className={styles.prize}>
      <Text size={Text.Sizes.SIZE_16} marginless>
        <Anchor href={Routes.EVENT_PRIZE(eventPath, prize.id)}>{prize.name}</Anchor>
      </Text>
      <Text size={Text.Sizes.SIZE_14} marginless>
        <strong>{CurrencyUtils.asCurrency(prize.minimumbid, { currency: event.paypalcurrency })}</strong>{' '}
        {prize.sumdonations ? 'Total Donations' : 'Minimum Single Donation'}
      </Text>
    </div>
  ) : (
    <></>
  );
};

const Prizes = ({ prizes }: { prizes: Prize[] }) => {
  const { SWEEPSTAKES_URL } = useConstants();
  const { id: eventId } = useEventFromRoute();

  return (
    <React.Fragment>
      <Header size={Header.Sizes.H3}>Prizes</Header>
      <div className={styles.container}>
        <div className={styles.prizeInfo}>
          <Text size={Text.Sizes.SIZE_16}>Donations can enter you to win prizes!</Text>
          <Text size={Text.Sizes.SIZE_16}>
            {eventId != null ? <Anchor href={Routes.EVENT_PRIZES(eventId)}>Full prize list</Anchor> : <LoadingDots />}
          </Text>
          <React.Fragment>
            <Text size={Text.Sizes.SIZE_16}>
              <Anchor href={SWEEPSTAKES_URL}>Official Rules</Anchor>
            </Text>
            <Text size={Text.Sizes.SIZE_16}>
              No donation necessary for a chance to win. See sweepstakes rules for details and instructions.
            </Text>
          </React.Fragment>
        </div>
        <div className={styles.prizeList}>
          <div className={styles.prizes}>{prizes?.map(prize => <PrizeRow key={prize.id} prize={prize} />)}</div>
        </div>
      </div>
    </React.Fragment>
  );
};

export default Prizes;
