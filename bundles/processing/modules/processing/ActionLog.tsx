import * as React from 'react';
import { useQuery } from 'react-query';
import { CSSTransition, TransitionGroup } from 'react-transition-group';
import { Anchor, Button, Header, Stack, Text } from '@spyrothon/sparx';

import APIClient from '@public/apiv2/APIClient';
import { Donation, DonationProcessAction } from '@public/apiv2/APITypes';
import * as CurrencyUtils from '@public/util/currency';
import Undo from '@uikit/icons/Undo';

import { AdminRoutes, useAdminRoute } from '../../Routes';
import { useMe } from '../auth/AuthStore';
import { useDonation } from '../donations/DonationsStore';
import RelativeTime from '../time/RelativeTime';
import { loadProcessActions, useOwnProcessActions } from './ProcessActionsStore';

import styles from './ActionLog.mod.css';

interface NoDonationActionRow {
  action: DonationProcessAction;
}

function NoDonationActionRow(props: NoDonationActionRow) {
  const { action } = props;

  return null;
}

interface DonationActionRow {
  action: DonationProcessAction;
  donation: Donation;
}

function DonationActionRow(props: DonationActionRow) {
  const { action, donation } = props;

  const donationLink = useAdminRoute(AdminRoutes.DONATION(action.donation_id));
  const amount = CurrencyUtils.asCurrency(donation.amount);
  const timestamp = React.useMemo(() => new Date(action.occurred_at), [action.occurred_at]);

  return (
    <Stack className={styles.action} direction="horizontal" justify="space-between" wrap={false} key={action.id}>
      <div className={styles.info}>
        <Text variant="text-sm/normal">
          <Anchor href={donationLink} newTab>
            #{action.donation_id}
          </Anchor>
          {' · '}
          <strong>{action.to_state}</strong>
          {' · '}
          <RelativeTime time={timestamp} forceRelative />
        </Text>
        <Text variant="text-sm/normal">
          {donation != null ? (
            <>
              <strong>{amount}</strong> from <strong>{donation.donor_name}</strong>
            </>
          ) : (
            'Donation info not available'
          )}
        </Text>
      </div>
      <Button
        variant="link"
        className={styles.undoButton}
        // eslint-disable-next-line react/jsx-no-bind
        // onClick={() => unprocess.mutate(action.donationId)}
        // disabled={unprocess.isLoading}
        title="Undo this action and bring the donation back to the main view">
        <Undo />
      </Button>
    </Stack>
  );
}

function ActionEntry({ action }: { action: DonationProcessAction }) {
  const storedDonation = useDonation(action.donation_id);
  const donation = action.donation ?? storedDonation;
  const hasDonation = donation != null || storedDonation;

  if (!hasDonation) {
    return <NoDonationActionRow action={action} />;
  }

  return <DonationActionRow action={action} donation={donation} />;
}

export default function ActionLog() {
  const me = useMe();
  // -1 should be an invalid user id, meaning we'll get back an empty history
  // until Me has loaded.
  const history = useOwnProcessActions(me?.id ?? -1);

  const { data: initialHistory } = useQuery(`processing.action-history`, () => APIClient.getProcessActionHistory(), {
    staleTime: 60 * 60 * 1000,
  });
  React.useEffect(() => {
    if (initialHistory == null) return;

    loadProcessActions(initialHistory);
  }, [initialHistory]);

  return (
    <div>
      <Header tag="h2" variant="header-sm/normal" withMargin>
        Action History
      </Header>
      <TransitionGroup>
        {history.slice(0, 10).map(action => (
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
