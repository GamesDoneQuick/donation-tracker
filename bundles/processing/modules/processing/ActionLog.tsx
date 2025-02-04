import * as React from 'react';
import { useMutation } from 'react-query';
import { CSSTransition, TransitionGroup } from 'react-transition-group';
import { Anchor, Button, Header, Text } from '@spyrothon/sparx';

import APIClient from '@public/apiv2/APIClient';
import { APIDonation as Donation } from '@public/apiv2/APITypes';
import * as CurrencyUtils from '@public/util/currency';
import Undo from '@uikit/icons/Undo';

import { AdminRoutes, useAdminRoute } from '../../Routes';
import { loadDonations, useDonation } from '../donations/DonationsStore';
import useProcessingStore, { HistoryAction } from '../processing/ProcessingStore';

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
      return APIClient.unprocessDonation(donationId);
    },
    {
      onSuccess: (donation: Donation) => {
        loadDonations([donation]);
        store.undoAction(action.id);
      },
    },
  );

  const amount = CurrencyUtils.asCurrency(donation.amount, { currency: donation.currency });

  return (
    <div className={styles.action} key={action.id}>
      <div className={styles.info}>
        <Text variant="header-xs/normal">
          <strong>{amount}</strong> from <strong>{donation.donor_name}</strong>
        </Text>
        <Text variant="text-sm/normal">
          <Anchor href={donationLink}>#{donation.id}</Anchor>
          {' – '}
          <span>{action.label}</span>
          {' – '}
          <span>{getRelativeTime(action.timestamp)}</span>
        </Text>
      </div>
      <Button
        variant="warning/outline"
        className={styles.undoButton}
        // eslint-disable-next-line react/jsx-no-bind
        onPress={() => unprocess.mutate(action.donationId)}
        isDisabled={unprocess.isLoading}
        aria-name="undo"
        aria-label="Undo this action and bring the donation back to the main view">
        <Undo />
      </Button>
    </div>
  );
}

export default function ActionLog() {
  const history = useProcessingStore(state => state.actionHistory.slice(0, 20));

  // This keeps the live timers relatively up-to-date.
  const [, forceUpdate] = React.useState({});
  React.useEffect(() => {
    const interval = setInterval(() => forceUpdate({}), Math.random() * 4000 + 6000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className={styles.sidebarHistory}>
      <Header tag="h2" variant="header-sm/normal" withMargin>
        Action History
      </Header>
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
