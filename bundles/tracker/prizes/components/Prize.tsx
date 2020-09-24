import React, { useCallback, useState } from 'react';
import { useSelector } from 'react-redux';

import * as CurrencyUtils from '../../../public/util/currency';
import TimeUtils, { DateTime } from '../../../public/util/TimeUtils';
import Anchor from '../../../uikit/Anchor';
import Button from '../../../uikit/Button';
import Container from '../../../uikit/Container';
import Header from '../../../uikit/Header';
import LoadingDots from '../../../uikit/LoadingDots';
import Markdown from '../../../uikit/Markdown';
import Text from '../../../uikit/Text';
import useDispatch from '../../hooks/useDispatch';
import * as EventActions from '../../events/EventActions';
import * as EventStore from '../../events/EventStore';
import RouterUtils, { Routes } from '../../router/RouterUtils';
import { StoreState } from '../../Store';
import * as PrizeActions from '../PrizeActions';
import * as PrizeStore from '../PrizeStore';
import * as PrizeTypes from '../PrizeTypes';
import * as PrizeUtils from '../PrizeUtils';
import { useGlobals } from '../../../common/Globals';

import styles from './Prize.mod.css';

type PrizeDonateButtonProps = {
  prize: PrizeTypes.Prize;
  now: DateTime;
  onClick: () => void;
};

const PrizeDonateButton = ({ prize, now, onClick }: PrizeDonateButtonProps) => {
  if (prize.startDrawTime == null || prize.endDrawTime == null) {
    return null;
  } else if (now > prize.startDrawTime && now < prize.endDrawTime) {
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

function getPrizeDetails(prize: PrizeTypes.Prize) {
  return [
    {
      name: 'Estimated Value',
      value: prize.estimatedValue != null ? CurrencyUtils.asCurrency(prize.estimatedValue) : undefined,
    },
    {
      name: 'Opening Run',
      value: prize.startRun != null ? prize.startRun.name : undefined,
    },
    {
      name: 'Opening Time',
      value:
        prize.startDrawTime != null
          ? `${prize.startDrawTime.toLocaleString(DateTime.DATETIME_MED)} (estimated)`
          : undefined,
    },
    {
      name: 'Closing Run',
      value: prize.endRun != null ? prize.endRun.name : undefined,
    },
    {
      name: 'Closing Time',
      value:
        prize.endDrawTime != null
          ? `${prize.endDrawTime.toLocaleString(DateTime.DATETIME_MED)} (estimated)`
          : undefined,
    },
  ];
}

type PrizeProps = {
  prizeId: string;
};

const Prize = (props: PrizeProps) => {
  const { SWEEPSTAKES_URL } = useGlobals();
  const { prizeId } = props;
  const now = TimeUtils.getNowLocal();

  const [prizeError, setPrizeError] = useState(false);
  const setPrizeErrorTrue = useCallback(() => setPrizeError(true), []);
  const dispatch = useDispatch();
  const { event, eventId, prize } = useSelector((state: StoreState) => {
    const prize = PrizeStore.getPrize(state, { prizeId });
    const event = prize != null ? EventStore.getEvent(state, { eventId: prize.eventId }) : undefined;

    return {
      event,
      eventId: prize != null ? prize.eventId : undefined,
      prize,
    };
  });

  React.useEffect(() => {
    dispatch(PrizeActions.fetchPrizes({ id: prizeId }));
  }, [dispatch]);

  React.useEffect(() => {
    if (event == null && eventId != null) {
      dispatch(EventActions.fetchEvents({ id: eventId }));
    }
  }, [dispatch, event, eventId]);

  const handleDonate = React.useCallback(() => {
    if (prize == null) return;
    RouterUtils.navigateTo(Routes.EVENT_DONATE(prize.eventId), {
      hash: prize.minimumBid != null ? prize.minimumBid.toFixed(2) : '',
      forceReload: true,
    });
  }, [prize]);

  if (prize == null)
    return (
      <Container size={Container.Sizes.WIDE}>
        <div className={styles.loadingDots}>
          <LoadingDots width="100%" />
        </div>
      </Container>
    );

  const prizeDetails = getPrizeDetails(prize);
  const prizeImage = prizeError ? null : PrizeUtils.getPrimaryImage(prize);

  const handleBack = () => {
    RouterUtils.navigateTo(Routes.EVENT_PRIZES(prize.eventId));
  };

  return (
    <Container size={Container.Sizes.WIDE}>
      <div className={styles.container}>
        <div className={styles.gallery}>
          {prizeImage != null ? (
            <img alt={prize.public} onError={setPrizeErrorTrue} className={styles.image} src={prizeImage} />
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
              {prize.public}
            </Header>
            <Text size={Text.Sizes.SIZE_16} color={Text.Colors.MUTED}>
              {event != null ? (
                <React.Fragment>
                  <strong className={styles.summaryItem}>
                    <Anchor href={event.canonicalUrl}>{event.public}</Anchor>
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
              <strong>{CurrencyUtils.asCurrency(prize.minimumBid)} </strong>
              {prize.sumDonations ? 'Total Donations' : 'Minimum Single Donation'}
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
            No donation necessary for a chance to win. See <Anchor href={SWEEPSTAKES_URL}>sweepstakes rules</Anchor> for
            details and instructions.
          </Text>
        </div>
      )}
    </Container>
  );
};

export default Prize;
