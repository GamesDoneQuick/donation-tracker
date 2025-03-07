import React from 'react';
import { useNavigate } from 'react-router';

import { useConstants } from '@common/Constants';
import APIErrorList from '@public/APIErrorList';
import { useEventFromRoute, useSplitRuns } from '@public/apiv2/hooks';
import { OrderedRun, Prize } from '@public/apiv2/Models';
import { useLazyPrizesQuery, useLazyRunsQuery } from '@public/apiv2/reducers/trackerApi';
import { useBooleanState } from '@public/hooks/useBooleanState';
import * as CurrencyUtils from '@public/util/currency';
import TimeUtils, { DateTime } from '@public/util/TimeUtils';
import Anchor from '@uikit/Anchor';
import Button from '@uikit/Button';
import Container from '@uikit/Container';
import Header from '@uikit/Header';
import LoadingDots from '@uikit/LoadingDots';
import Markdown from '@uikit/Markdown';
import Text from '@uikit/Text';

import RouterUtils, { Routes as TrackerRoutes } from '@tracker/router/RouterUtils';

import * as PrizeUtils from '../PrizeUtils';

import styles from './Prize.mod.css';

type PrizeDonateButtonProps = {
  prize: Prize;
  now: DateTime;
  onClick: () => void;
};

const PrizeDonateButton = ({ prize, now, onClick }: PrizeDonateButtonProps) => {
  if (prize.start_draw_time == null || prize.end_draw_time == null) {
    return null;
  } else if (now > prize.start_draw_time && now < prize.end_draw_time) {
    return (
      <div className={styles.donateNow}>
        <Button className={styles.donateButton} onClick={onClick}>
          Donate Now
        </Button>
      </div>
    );
  }

  return null;
};

function getPrizeDetails(prize: Prize | undefined, currency: string, runs: OrderedRun[]) {
  return prize != null
    ? [
        {
          name: 'Estimated Value',
          value:
            prize.estimatedvalue != null ? CurrencyUtils.asCurrency(prize.estimatedvalue, { currency }) : undefined,
        },
        {
          name: 'Opening Run',
          value: prize.startrun != null && runs.find(r => r.id === prize.startrun)?.name,
        },
        {
          name: 'Opening Time',
          value: prize.start_draw_time && `${prize.start_draw_time.toLocaleString(DateTime.DATETIME_MED)} (estimated)`,
        },
        {
          name: 'Closing Run',
          value: prize.endrun != null && runs.find(r => r.id === prize.endrun)?.name,
        },
        {
          name: 'Closing Time',
          value:
            prize.end_draw_time != null && `${prize.end_draw_time.toLocaleString(DateTime.DATETIME_MED)} (estimated)`,
        },
      ]
    : [];
}

type PrizeProps = {
  prizeId: number;
};

const PrizeDetail = (props: PrizeProps) => {
  const { SWEEPSTAKES_URL } = useConstants();
  const { prizeId } = props;
  const now = TimeUtils.getNowLocal();

  const { data: event, id: eventId, path: eventPath, error: eventError, isLoading: eventLoading } = useEventFromRoute();
  const [getRuns, { data: runs, error: runsError, isLoading: runsLoading }] = useLazyRunsQuery({
    pollingInterval: 300000,
  });
  const [orderedRuns] = useSplitRuns(runs);

  const [getPrizes, { data: prize, error: prizeError, isLoading: prizeLoading }] = useLazyPrizesQuery({
    pollingInterval: 300000,
    selectFromResult: ({ data, error, ...rest }) => {
      const prize = data?.find(p => p.id === prizeId);
      return {
        data: prize,
        error: !prize && rest.isSuccess ? { status: 404, statusText: 'Prize does not exist in provided query' } : error,
        ...rest,
      };
    },
  });

  React.useEffect(() => {
    if (eventId != null) {
      getRuns({ urlParams: eventId }, true);
      getPrizes({ urlParams: eventId }, true);
    }
  }, [eventId, getPrizes, getRuns]);

  const currency = event?.paypalcurrency || 'USD';

  const navigate = useNavigate();

  const handleDonate = React.useCallback(() => {
    if (prize == null) return;
    RouterUtils.navigateTo(navigate, TrackerRoutes.EVENT_DONATE(eventPath), {
      hash: prize.minimumbid != null ? prize.minimumbid.toFixed(2) : '',
      forceReload: true,
    });
  }, [eventPath, navigate, prize]);

  const handleBack = React.useCallback(() => {
    if (prize) {
      RouterUtils.navigateTo(navigate, TrackerRoutes.EVENT_PRIZES(eventPath));
    }
  }, [eventPath, navigate, prize]);

  const prizeDetails = getPrizeDetails(prize, currency, orderedRuns);
  const [imageError, setImageErrorTrue] = useBooleanState(false);
  const prizeImage = imageError ? null : PrizeUtils.getPrimaryImage(prize);

  return (
    <Container size={Container.Sizes.WIDE}>
      {eventLoading || runsLoading || prizeLoading ? (
        <div className={styles.loadingDots}>
          <LoadingDots width="100%" />
        </div>
      ) : (
        <APIErrorList errors={[eventError, runsError, prizeError]}>
          {prize && (
            <>
              <div className={styles.container}>
                <div className={styles.gallery}>
                  {prizeImage != null ? (
                    <img alt={prize.name} onError={setImageErrorTrue} className={styles.image} src={prizeImage} />
                  ) : (
                    <div className={styles.noImage}>
                      <Header size={Header.Sizes.H4} color={Header.Colors.MUTED}>
                        No Image Provided
                      </Header>
                    </div>
                  )}
                </div>
                <div className={styles.content}>
                  <div className={styles.summary}>
                    <Header size={Header.Sizes.H1} className={styles.prizeHeader}>
                      {prize.name}
                    </Header>
                    <Text size={Text.Sizes.SIZE_16} color={Text.Colors.MUTED}>
                      {event != null ? (
                        <React.Fragment>
                          <strong className={styles.summaryItem}>
                            <Anchor href={`/tracker/event/${event.id}`}>{event.name}</Anchor>
                          </strong>
                          &nbsp;&middot;&nbsp;
                        </React.Fragment>
                      ) : null}
                      {prize.provider != null ? (
                        <span className={styles.summaryItem}>
                          Provided by <strong>{prize.provider}</strong>
                        </span>
                      ) : null}
                    </Text>
                    <Text size={Text.Sizes.SIZE_20}>
                      <strong>{CurrencyUtils.asCurrency(prize.minimumbid, { currency })} </strong>
                      {prize.sumdonations ? 'Total Donations' : 'Minimum Single Donation'}
                    </Text>

                    <PrizeDonateButton prize={prize} now={now} onClick={handleDonate} />
                  </div>

                  <hr className={styles.divider} />

                  {prize.description != null && prize.description.length !== 0 ? (
                    <React.Fragment>
                      <Text className={styles.description}>
                        <Markdown>{prize.description}</Markdown>
                      </Text>
                      <hr className={styles.divider} />
                    </React.Fragment>
                  ) : null}

                  <div className={styles.details}>
                    {prizeDetails.map(({ name, value }) =>
                      value != null ? (
                        <Text key={name} size={Text.Sizes.SIZE_14}>
                          <strong>{name}:</strong> <span className={styles.detailValue}>{value}</span>
                        </Text>
                      ) : null,
                    )}
                  </div>

                  <Button look={Button.Looks.OUTLINED} onClick={handleBack}>
                    Back to Prizes
                  </Button>
                </div>
              </div>

              {SWEEPSTAKES_URL && (
                <div className={styles.disclaimers}>
                  <Text>
                    No donation necessary for a chance to win. See{' '}
                    <Anchor href={SWEEPSTAKES_URL}>sweepstakes rules</Anchor> for details and instructions.
                  </Text>
                </div>
              )}
            </>
          )}
        </APIErrorList>
      )}
    </Container>
  );
};

export default PrizeDetail;
