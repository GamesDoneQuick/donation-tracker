import * as React from 'react';
import { useMutation, useQuery } from 'react-query';
import { Anchor, Button, Card, Checkbox, Header, openModal, Stack, Text, useTooltip } from '@spyrothon/sparx';

import APIClient from '@public/apiv2/APIClient';
import { DonationProcessAction } from '@public/apiv2/APITypes';
import * as CurrencyUtils from '@public/util/currency';
import Undo from '@uikit/icons/Undo';

import { AdminRoutes, useAdminRoute } from '../../Routes';
import { useMe } from '../auth/AuthStore';
import { useDonation } from '../donations/DonationsStore';
import RelativeTime from '../time/RelativeTime';
import { loadProcessActions, useOwnProcessActions } from './ProcessActionsStore';

import styles from './ActionHistoryModal.mod.css';

export function ActionHistoryModalButton() {
  function handleOpen() {
    openModal(() => <ActionHistoryModal />);
  }

  return <Button onClick={handleOpen}>View Action History</Button>;
}

function ActionEntry({ action }: { action: DonationProcessAction }) {
  const storedDonation = useDonation(action.donation_id);
  const donation = action.donation ?? storedDonation;
  const hasDonation = donation != null;
  const isUndo = action.originating_action != null;

  const donationLink = useAdminRoute(AdminRoutes.DONATION(action.donation_id));
  const amount = CurrencyUtils.asCurrency(donation.amount);
  const timestamp = React.useMemo(() => new Date(action.occurred_at), [action.occurred_at]);

  const [undoTooltipProps] = useTooltip<HTMLButtonElement>(`Reset to ${action.from_state}`);
  const undo = useMutation(() => APIClient.undoProcessAction(action.id));

  return (
    <Card className={styles.action}>
      <Stack direction="horizontal" justify="space-between" wrap={false} key={action.id}>
        <div>
          <Text variant="text-sm/normal">
            {isUndo ? (
              <em>
                Undo <strong>{action.from_state}</strong> to <strong>{action.to_state}</strong>
              </em>
            ) : (
              <strong>{action.to_state}</strong>
            )}
            {' · '}
            <RelativeTime time={timestamp} forceRelative />
          </Text>
          <Text variant="text-sm/normal">
            <Anchor href={donationLink} newTab>
              #{action.donation_id}
            </Anchor>
            {' · '}
            {hasDonation ? (
              <>
                <strong>{amount}</strong> from <strong>{donation.donor_name}</strong>
              </>
            ) : (
              'Donation info not available'
            )}
          </Text>
          {donation?.comment != null ? (
            <Text className={styles.comment} variant="text-xs/normal">
              {donation.comment.slice(0, 500)}
              {donation.comment.length > 500 ? '...' : null}
            </Text>
          ) : null}
        </div>
        {!isUndo ? (
          <Button
            {...undoTooltipProps}
            variant="link"
            // eslint-disable-next-line react/jsx-no-bind
            onClick={() => undo.mutate()}
            disabled={undo.isLoading}>
            <Undo />
          </Button>
        ) : null}
      </Stack>
    </Card>
  );
}

export default function ActionHistoryModal() {
  const me = useMe();
  // -1 should be an invalid user id, meaning we'll get back an empty history
  // until Me has loaded.
  const history = useOwnProcessActions(me?.id ?? -1);

  const [showUndos, setShowUndos] = React.useState(true);

  const { data: initialHistory } = useQuery(`processing.action-history`, () => APIClient.getProcessActionHistory(), {
    // This data comes in over the socket as the user interacts with the page.
    // This initial fetch is just to back-populate data when they open the modal,
    // So it only needs to run once-ish.
    cacheTime: 60 * 60 * 1000,
    staleTime: 60 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
  React.useEffect(() => {
    if (initialHistory == null) return;

    loadProcessActions(initialHistory);
  }, [initialHistory]);

  return (
    <Card className={styles.container}>
      <Stack as={Header} direction="horizontal" justify="space-between" tag="h1" variant="header-md/normal" withMargin>
        Action History
        <Checkbox
          checked={showUndos}
          // eslint-disable-next-line react/jsx-no-bind
          onChange={event => setShowUndos(event.target.checked)}
          label="Show Undos"
        />
      </Stack>
      <Stack align="stretch">
        {history.map(action => {
          if (!showUndos && action.originating_action != null) return null;
          return <ActionEntry key={action.id} action={action} />;
        })}
      </Stack>
    </Card>
  );
}
