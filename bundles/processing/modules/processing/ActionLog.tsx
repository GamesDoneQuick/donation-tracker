import React from 'react';
import { CSSTransition, TransitionGroup } from 'react-transition-group';
import { Anchor, Button, Header, Text } from '@faulty/gdq-design';

import APIErrorList from '@public/APIErrorList';
import { useDonation, useUnprocessDonationMutation } from '@public/apiv2/hooks';
import { useNow } from '@public/hooks/useNow';
import * as CurrencyUtils from '@public/util/currency';
import Undo from '@uikit/icons/Undo';

import { AdminRoutes, useAdminRoute } from '../../Routes';
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
  const { data: donation } = useDonation(action.donationId);
  const { undoAction } = useProcessingStore();

  const [unprocess, unprocessResult] = useUnprocessDonationMutation();
  const mutation = React.useCallback(async () => {
    const { error } = await unprocess(action.donationId);
    if (error == null) {
      undoAction(action.id);
    }
  }, [action, undoAction, unprocess]);

  if (donation == null) {
    return null;
  }
  const amount = CurrencyUtils.asCurrency(donation.amount, { currency: donation.currency });

  return (
    <div className={styles.action}>
      <APIErrorList errors={unprocessResult.error} />
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
        onPress={mutation}
        isDisabled={unprocessResult.isLoading}
        aria-name="undo"
        aria-label="Undo this action and bring the donation back to the main view">
        <Undo />
      </Button>
    </div>
  );
}

export default function ActionLog() {
  const history = useProcessingStore(state => state.actionHistory.slice(0, 20));

  // keeps the relative timers up to date
  useNow(10000);

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
            <ActionEntry action={action} />
          </CSSTransition>
        ))}
      </TransitionGroup>
    </div>
  );
}
