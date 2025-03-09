import React from 'react';
import { Duration, Interval } from 'luxon';

import { useConstants } from '@common/Constants';
import APIErrorList from '@public/APIErrorList';
import { useEventFromRoute } from '@public/apiv2/hooks';
import { Prize, TimedPrize } from '@public/apiv2/Models';
import { useLazyPrizesQuery, useLazyRunsQuery } from '@public/apiv2/reducers/trackerApi';
import { useNow } from '@public/hooks/useNow';
import Title from '@public/Title';
import Anchor from '@uikit/Anchor';
import Container from '@uikit/Container';
import Header from '@uikit/Header';
import LoadingDots from '@uikit/LoadingDots';
import Text from '@uikit/Text';

import PrizeCard from './PrizeCard';

import styles from './Prizes.mod.css';

// The limit of how many prizes should be included in sections that appear
// above the All Prizes section. This generally avoids showing prizes multiple
// times, and keeps the page organized when large blocks of prizes open and
// close near the same time.

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
          <PrizeCard key={prize.id} currency={currency} prize={prize} />
        ))}
      </div>
    </section>
  );
};

const Prizes = () => {
  const { SWEEPSTAKES_URL } = useConstants();

  const now = useNow();
  const { data: event, id: eventId, error: eventError, isLoading: eventLoading } = useEventFromRoute();
  const [getPrizes, { data: prizes, error: prizesError, isLoading: prizesLoading }] = useLazyPrizesQuery({
    pollingInterval: 300000,
  });
  // the list doesn't need it but the cards do
  const [getRuns, { error: runsError, isLoading: runsLoading }] = useLazyRunsQuery({ pollingInterval: 300000 });
  const soonInterval = React.useMemo(() => Interval.after(now, Duration.fromObject({ hours: 4 })), [now]);
  const closingPrizes = React.useMemo(
    () =>
      (prizes || [])
        .filter(
          (prize): prize is TimedPrize => prize.end_draw_time != null && soonInterval.contains(prize.end_draw_time),
        )
        .sort((prize1, prize2) => prize1.end_draw_time.toMillis() - prize2.end_draw_time.toMillis()),
    [prizes, soonInterval],
  );

  React.useEffect(() => {
    if (eventId != null) {
      getPrizes({ urlParams: eventId }, true);
      getRuns({ urlParams: eventId }, true);
    }
  }, [eventId, getPrizes, getRuns]);

  return (
    <Container size={Container.Sizes.WIDE}>
      <Title>{event?.name}</Title>
      <APIErrorList errors={[eventError, prizesError, runsError]}>
        {eventLoading ? (
          <div className={styles.loadingDots}>
            <LoadingDots width="100%" />
          </div>
        ) : (
          event && (
            <>
              <Header size={Header.Sizes.H1} className={styles.pageHeader}>
                Prizes for <span className={styles.eventName}>{event?.name}</span>
              </Header>
              {SWEEPSTAKES_URL && (
                <div style={{ textAlign: 'center' }}>
                  <Text size={Text.Sizes.SIZE_12}>
                    No donation necessary for a chance to win. See{' '}
                    <Anchor href={SWEEPSTAKES_URL}>sweepstakes rules</Anchor> for details and instructions.
                  </Text>
                </div>
              )}
              {prizesLoading || runsLoading ? (
                <div className={styles.loadingDots}>
                  <LoadingDots width="100%" />
                </div>
              ) : (
                <>
                  {closingPrizes.length > 0 && (
                    <>
                      <PrizeGrid prizes={closingPrizes} currency={event.paypalcurrency} name="Closing Soon!" />
                      <hr className={styles.divider} />
                    </>
                  )}
                  {prizes && <PrizeGrid prizes={prizes} currency={event.paypalcurrency} name="All Prizes" />}
                </>
              )}
            </>
          )
        )}
      </APIErrorList>
    </Container>
  );
};

export default Prizes;
