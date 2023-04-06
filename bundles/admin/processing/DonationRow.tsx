import * as React from 'react';
import Highlighter from 'react-highlight-words';
import { useMutation, UseMutationResult } from 'react-query';
import { Anchor, Button, ButtonVariant, Stack, Text, useTooltip } from '@spyrothon/sparx';

import { usePermission } from '@public/api/helpers/auth';
import APIClient from '@public/apiv2/APIClient';
import type { Donation, DonationBid } from '@public/apiv2/APITypes';
import * as CurrencyUtils from '@public/util/currency';
import TimeUtils from '@public/util/TimeUtils';
import Approve from '@uikit/icons/Approve';
import Deny from '@uikit/icons/Deny';
import SendForward from '@uikit/icons/SendForward';

import getEstimatedReadingTime from './getEstimatedReadingTIme';
import useProcessingStore from './ProcessingStore';
import { AdminRoutes, useAdminRoute } from './Routes';

import styles from './DonationRow.mod.css';

function useDonationMutation(mutation: (donationId: number) => Promise<Donation>, actionLabel: string) {
  const store = useProcessingStore();
  return useMutation(mutation, {
    onSuccess: (donation: Donation) => store.processDonation(donation, actionLabel),
  });
}

interface MutationButtonProps<T> {
  mutation: UseMutationResult<T, unknown, number, unknown>;
  donationId: number;
  label: string;
  icon: React.ComponentType;
  variant?: ButtonVariant;
  disabled?: boolean;
}

function MutationButton<T>(props: MutationButtonProps<T>) {
  const { mutation, donationId, variant = 'default', label, icon: Icon, disabled = false } = props;

  const [tooltipProps] = useTooltip<HTMLButtonElement>(label);

  return (
    <Button
      {...tooltipProps}
      // eslint-disable-next-line react/jsx-no-bind
      onClick={() => mutation.mutate(donationId)}
      disabled={disabled || mutation.isLoading}
      variant={variant}>
      <Icon />
    </Button>
  );
}

interface BidsRowProps {
  bids: DonationBid[];
}

function BidsRow(props: BidsRowProps) {
  const { bids } = props;
  if (bids.length === 0) return null;

  const bidNames = bids.map(bid => `${bid.bid_name} (${CurrencyUtils.asCurrency(bid.amount)})`);

  return (
    <Text variant="text-sm/normal" className={styles.bids}>
      Attached Bids: {bidNames.join(' • ')}
    </Text>
  );
}

interface DonationRowProps {
  donation: Donation;
  action: (donationId: string) => Promise<Donation>;
  actionName: string;
  actionLabel: string;
}

export default function DonationRow(props: DonationRowProps) {
  const { donation, action, actionName, actionLabel } = props;
  const timestamp = TimeUtils.parseTimestamp(donation.timereceived);

  const donationLink = useAdminRoute(AdminRoutes.DONATION(donation.id));
  const donorLink = useAdminRoute(AdminRoutes.DONOR(donation.donor));
  const canEditDonors = usePermission('tracker.change_donor');

  const keywords = useProcessingStore(state => state.keywords);
  const mutation = useDonationMutation((donationId: number) => action(`${donationId}`), actionName);
  const approve = useDonationMutation(
    (donationId: number) => APIClient.approveDonationComment(`${donationId}`),
    'Approved',
  );
  const deny = useDonationMutation((donationId: number) => APIClient.denyDonationComment(`${donationId}`), 'Blocked');

  const readingTime = getEstimatedReadingTime(donation.comment);
  const amount = CurrencyUtils.asCurrency(donation.amount);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Stack direction="horizontal" justify="space-between" align="center" className={styles.headerTop}>
          <div className={styles.title}>
            <Text variant="header-sm/normal">
              <strong>{amount}</strong>
              <Text tag="span" variant="text-md/secondary">
                {' from '}
              </Text>
              <strong>
                <Highlighter
                  highlightClassName={styles.highlighted}
                  searchWords={keywords}
                  textToHighlight={donation.donor_name || ''}
                />
              </strong>
            </Text>
            <Text variant="text-xs/secondary">
              <Anchor href={donationLink}>Edit Donation</Anchor>
              {canEditDonors && donation.donor != null ? (
                <>
                  {' · '}
                  <Anchor href={donorLink}>Edit Donor</Anchor>
                </>
              ) : null}
              {' · '}
              <span>{timestamp.toFormat('hh:mm:ss a')}</span>
              {' · '}
              <span>{readingTime} to read</span>
            </Text>
          </div>
          <Stack direction="horizontal">
            <MutationButton
              mutation={mutation}
              donationId={donation.id}
              icon={SendForward}
              variant="success"
              label={actionLabel}
            />
            <MutationButton mutation={approve} donationId={donation.id} icon={Approve} label="Approve Only" />
            <MutationButton mutation={deny} donationId={donation.id} icon={Deny} label="Block" variant="danger" />
          </Stack>
        </Stack>
        <BidsRow bids={donation.bids} />
      </div>
      <Text className={styles.comment}>
        <Highlighter
          highlightClassName={styles.highlighted}
          searchWords={keywords}
          textToHighlight={donation.comment || ''}
        />
      </Text>
    </div>
  );
}
