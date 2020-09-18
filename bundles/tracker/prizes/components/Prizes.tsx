import * as React from 'react';
import { useSelector } from 'react-redux';

import TimeUtils from '../../../public/util/TimeUtils';
import Container from '../../../uikit/Container';
import Header from '../../../uikit/Header';
import LoadingDots from '../../../uikit/LoadingDots';
import * as EventActions from '../../events/EventActions';
import * as EventStore from '../../events/EventStore';
import useDispatch from '../../hooks/useDispatch';
import { StoreState } from '../../Store';
import * as PrizeActions from '../PrizeActions';
import * as PrizeStore from '../PrizeStore';
import PrizeCard from './PrizeCard';
import { Prize } from '../PrizeTypes';

import styles from './Prizes.mod.css';
import Text from '../../../uikit/Text';
import Anchor from '../../../uikit/Anchor';
import { useGlobals } from '../../../common/Globals';

// The limit of how many prizes should be included in sections that appear
// above the All Prizes section. This generally avoids showing prizes multiple
// times, and keeps the page organized when large blocks of prizes open and
// close near the same time.
const FEATURED_SECTION_LIMIT = 6;

type PrizeGridProps = {
  prizes: Prize[];
  name: string;
};

const PrizeGrid = (props: PrizeGridProps) => {
  const { prizes, name } = props;

  return (
    <section className={styles.section}>
      <Header size={Header.Sizes.H3} className={styles.sectionHeader}>
        {name}
      </Header>
      <div className={styles.grid}>
        {prizes.map(prize => (
          <PrizeCard key={prize.id} prizeId={prize.id} />
        ))}
      </div>
    </section>
  );
};

type PrizesProps = {
  eventId: string;
};

const Prizes = (props: PrizesProps) => {
  const { SWEEPSTAKES_URL } = useGlobals();
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
  }, [eventId]);

  React.useEffect(() => {
    if (event != null) return;
    dispatch(EventActions.fetchEvents({ id: eventId }));
  }, [event, eventId]);

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
              <PrizeGrid prizes={closingPrizes} name="Closing Soon!" />
              <hr className={styles.divider} />
            </React.Fragment>
          )}
          <PrizeGrid prizes={allPrizes} name="All Prizes" />
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
