import React from 'react';
import { useSelector } from 'react-redux';

import { useConstants } from '@common/Constants';
import * as CurrencyUtils from '@public/util/currency';
import Anchor from '@uikit/Anchor';
import Header from '@uikit/Header';
import Text from '@uikit/Text';

import * as EventDetailsStore from '@tracker/event_details/EventDetailsStore';
import { Prize } from '@tracker/event_details/EventDetailsTypes';
import { Routes } from '@tracker/router/RouterUtils';

import styles from './DonationPrizes.mod.css';

type PrizeProps = {
  prize: Prize;
  eventId: string | number;
};

const PrizeRow = (props: PrizeProps) => {
  const { eventId, prize } = props;
  const currency = useSelector(EventDetailsStore.getEventCurrency);

  return (
    <div className={styles.prize}>
      <Text size={Text.Sizes.SIZE_16} marginless>
        {prize.url != null ? <Anchor href={Routes.EVENT_PRIZE(eventId, prize.id)}>{prize.name}</Anchor> : prize.name}
      </Text>
      <Text size={Text.Sizes.SIZE_14} marginless>
        <strong>{CurrencyUtils.asCurrency(prize.minimumbid, { currency })}</strong>{' '}
        {prize.sumdonations ? 'Total Donations' : 'Minimum Single Donation'}
      </Text>
    </div>
  );
};

type PrizesProps = {
  eventId: string | number;
};

const Prizes = (props: PrizesProps) => {
  const { SWEEPSTAKES_URL } = useConstants();
  const { eventId } = props;
  const { prizes } = useSelector(EventDetailsStore.getEventDetails);

  return (
    <React.Fragment>
      <Header size={Header.Sizes.H3}>Prizes</Header>
      <div className={styles.container}>
        <div className={styles.prizeInfo}>
          <Text size={Text.Sizes.SIZE_16}>Donations can enter you to win prizes!</Text>
          <Text size={Text.Sizes.SIZE_16}>
            <Anchor href={Routes.EVENT_PRIZES(eventId)}>Full prize list</Anchor>
          </Text>
          {SWEEPSTAKES_URL && (
            <React.Fragment>
              <Text size={Text.Sizes.SIZE_16}>
                <Anchor href={SWEEPSTAKES_URL}>Official Rules</Anchor>
              </Text>
              <Text size={Text.Sizes.SIZE_16}>
                No donation necessary for a chance to win. See sweepstakes rules for details and instructions.
              </Text>
            </React.Fragment>
          )}
        </div>
        <div className={styles.prizeList}>
          <div className={styles.prizes}>
            {prizes.map(prize => (
              <PrizeRow key={prize.id} prize={prize} eventId={eventId} />
            ))}
          </div>
        </div>
      </div>
    </React.Fragment>
  );
};

export default Prizes;
