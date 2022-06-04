import * as React from 'react';
import { useMutation } from 'react-query';
import { CSSTransition, TransitionGroup } from 'react-transition-group';

import APIClient from '@public/apiv2/APIClient';
import { Donation } from '@public/apiv2/APITypes';
import * as CurrencyUtils from '@public/util/currency';
import Undo from '@uikit/icons/Undo';

import Button from './Button';
import useProcessingStore, { HistoryAction, useDonation } from './ProcessingStore';
import { AdminRoutes, useAdminRoute } from './Routes';

import styles from './ActionLog.mod.css';

const timeFormatter = new Intl.RelativeTimeFormat('en', { style: 'narrow' });

function getRelativeTime(timestamp: number, now: number = Date.now()) {
  const diff = -(now - timestamp) / 1000;
  if (diff > -5) {
    return 'just now';
  } else if (diff <= -3600) {
    return timeFormatter.format(Math.round(diff / 3600), 'hours');
  } else if (diff <= -60) {
    return timeFormatter.format(Math.round(diff / 60), 'minutes');
  } else {
    return timeFormatter.format(Math.round(diff), 'seconds');
  }
}

function ActionEntry({ action }: { action: HistoryAction }) {
  const donationLink = useAdminRoute(AdminRoutes.DONATION(action.donationId));
  const donation = useDonation(action.donationId);

  const store = useProcessingStore();
  const unprocess = useMutation(
    (donationId: number) => {
      return APIClient.unprocessDonation(`${donationId}`);
    },
    {
      onSuccess: (donation: Donation) => {
        store.loadDonations([donation]);
        store.undoAction(action.id);
      },
    },
  );

  const amount = CurrencyUtils.asCurrency(donation.amount);

  return (
    <div className={styles.action} key={action.id}>
      <div className={styles.info}>
        <span className={styles.name}>
          <strong>{amount}</strong> from <strong>{donation.donor_name}</strong>
        </span>
        <div className={styles.byline}>
          <a href={donationLink} target="_blank" rel="noreferrer">
            #{donation.id}
          </a>
          {' – '}
          <span className={styles.actionName}>{action.label}</span>
          {' – '}
          <span className={styles.timestamp}>{getRelativeTime(action.timestamp)}</span>
        </div>
      </div>
      <div className={styles.undoAction}>
        <Button
          className={styles.undoButton}
          // eslint-disable-next-line react/jsx-no-bind
          onClick={() => unprocess.mutate(action.donationId)}
          disabled={unprocess.isLoading}
          title="Undo this action and bring the donation back to the main view"
          color="warning">
          <Undo />
        </Button>
      </div>
    </div>
  );
}

export default function ActionLog() {
  const history = useProcessingStore(state => state.actionHistory.slice(0, 20));

  const [, forceUpdate] = React.useState({});
  React.useEffect(() => {
    const interval = setInterval(() => forceUpdate({}), Math.random() * 4000 + 6000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className={styles.sidebarHistory}>
      <h5>Action History</h5>
      <TransitionGroup>
        {history.map(action => (
          <CSSTransition
            key={action.id}
            timeout={240}
            classNames={{
              enter: styles.actionEnter,
              enterActive: styles.actionEnterActive,
              exit: styles.actionExitActive,
              exitActive: styles.actionExit,
            }}>
            <ActionEntry key={action.id} action={action} />
          </CSSTransition>
        ))}
      </TransitionGroup>
    </div>
  );
}
