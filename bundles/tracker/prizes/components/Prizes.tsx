import React from 'react';
import { useSelector } from 'react-redux';

import { useConstants } from '@common/Constants';
import TimeUtils from '@public/util/TimeUtils';
import Anchor from '@uikit/Anchor';
import Container from '@uikit/Container';
import Header from '@uikit/Header';
import LoadingDots from '@uikit/LoadingDots';
import Text from '@uikit/Text';

import * as EventActions from '@tracker/events/EventActions';
import * as EventStore from '@tracker/events/EventStore';
import useDispatch from '@tracker/hooks/useDispatch';
import { StoreState } from '@tracker/Store';

import * as PrizeActions from '../PrizeActions';
import * as PrizeStore from '../PrizeStore';
import { Prize } from '../PrizeTypes';
import PrizeCard from './PrizeCard';

import styles from './Prizes.mod.css';

// The limit of how many prizes should be included in sections that appear
// above the All Prizes section. This generally avoids showing prizes multiple
// times, and keeps the page organized when large blocks of prizes open and
// close near the same time.
const FEATURED_SECTION_LIMIT = 6;

type PrizeGridProps = {
  prizes: Prize[];
  name: string;
  currency: string;
};

const PrizeGrid = (props: PrizeGridProps) => {
  const { prizes, name, currency } = props;

  return (
    <section className={styles.section}>
      <Header size={Header.Sizes.H3} className={styles.sectionHeader}>
        {name}
      </Header>
      <div className={styles.grid}>
        {prizes.map(prize => (
          <PrizeCard key={prize.id} currency={currency} prizeId={prize.id} />
        ))}
      </div>
    </section>
  );
};

type PrizesProps = {
  eventId: string;
};

const Prizes = (props: PrizesProps) => {
  const { SWEEPSTAKES_URL } = useConstants();
  const dispatch = useDispatch();
  const { eventId } = props;

  const now = TimeUtils.getNowLocal();

  const [loadingPrizes, setLoadingPrizes] = React.useState(false);

  const { closingPrizes, allPrizes, event } = useSelector((state: StoreState) => ({
    closingPrizes: PrizeStore.getPrizesClosingSoon(state, { targetTime: now }).slice(0, FEATURED_SECTION_LIMIT),
    allPrizes: PrizeStore.getSortedPrizes(state),
    event: EventStore.getEvent(state, { eventId }),
  }));

  React.useEffect(() => {
    setLoadingPrizes(true);
    dispatch(PrizeActions.fetchPrizes({ event: eventId })).finally(() => setLoadingPrizes(false));
  }, [dispatch, eventId]);

  React.useEffect(() => {
    if (event != null) return;
    dispatch(EventActions.fetchEvents({ id: eventId }));
  }, [dispatch, event, eventId]);

  if (event == null) {
    return (
      <Container size={Container.Sizes.WIDE}>
        <div className={styles.loadingDots}>
          <LoadingDots width="100%" />
        </div>
      </Container>
    );
  }

  return (
    <Container size={Container.Sizes.WIDE}>
      <Header size={Header.Sizes.H1} className={styles.pageHeader}>
        Prizes for <span className={styles.eventName}>{event.name}</span>
      </Header>
      {SWEEPSTAKES_URL && (
        <div style={{ textAlign: 'center' }}>
          <Text size={Text.Sizes.SIZE_12}>
            No donation necessary for a chance to win. See <Anchor href={SWEEPSTAKES_URL}>sweepstakes rules</Anchor> for
            details and instructions.
          </Text>
        </div>
      )}
      {!loadingPrizes ? (
        <React.Fragment>
          {closingPrizes.length > 0 && (
            <React.Fragment>
              <PrizeGrid prizes={closingPrizes} currency={event.paypalCurrency} name="Closing Soon!" />
              <hr className={styles.divider} />
            </React.Fragment>
          )}
          <PrizeGrid prizes={allPrizes} currency={event.paypalCurrency} name="All Prizes" />
        </React.Fragment>
      ) : (
        <div className={styles.loadingDots}>
          <LoadingDots width="100%" />
        </div>
      )}
    </Container>
  );
};

export default Prizes;
