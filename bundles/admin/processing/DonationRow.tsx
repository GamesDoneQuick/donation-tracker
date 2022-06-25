import * as React from 'react';
import Highlighter from 'react-highlight-words';
import { useMutation, UseMutationResult } from 'react-query';

import { usePermission } from '@public/api/helpers/auth';
import APIClient from '@public/apiv2/APIClient';
import type { Donation, DonationBid } from '@public/apiv2/APITypes';
import * as CurrencyUtils from '@public/util/currency';
import TimeUtils from '@public/util/TimeUtils';
import Approve from '@uikit/icons/Approve';
import Deny from '@uikit/icons/Deny';
import SendForward from '@uikit/icons/SendForward';

import Button from './Button';
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

interface MutationButtonProps<T> extends Omit<React.ComponentProps<typeof Button>, 'onClick' | 'children'> {
  mutation: UseMutationResult<T, unknown, number, unknown>;
  donationId: number;
  label: string;
}

function MutationButton<T>(props: MutationButtonProps<T>) {
  const { mutation, donationId, color = 'default', label, icon, disabled = false } = props;

  return (
    <Button
      // eslint-disable-next-line react/jsx-no-bind
      onClick={() => mutation.mutate(donationId)}
      disabled={disabled || mutation.isLoading}
      icon={icon}
      color={color}>
      {label}
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

  return <div className={styles.bids}>Attached Bids: {bidNames.join(' • ')}</div>;
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
        <div className={styles.headerTop}>
          <div className={styles.title}>
            <div className={styles.titleName}>
              <strong>{amount}</strong> from <strong>{donation.donor_name}</strong>
            </div>
            <div className={styles.titleByline}>
              <strong>
                <a href={donationLink} target="_blank" rel="noreferrer">
                  Edit Donation
                </a>
              </strong>
              {canEditDonors && donation.donor != null ? (
                <>
                  {' · '}
                  <a href={donorLink} target="_blank" rel="noreferrer">
                    Edit Donor
                  </a>
                </>
              ) : null}
              {' · '}
              <span className={styles.timestamp}>{timestamp.toFormat('hh:mm:ss a')}</span>
              {' · '}
              <span className={styles.readingTime}>{readingTime} to read</span>
            </div>
          </div>
          <div className={styles.actions}>
            <MutationButton
              mutation={mutation}
              donationId={donation.id}
              icon={SendForward}
              color="success"
              label={actionLabel}
            />
            <MutationButton mutation={approve} donationId={donation.id} icon={Approve} label="Approve Only" />
            <MutationButton mutation={deny} donationId={donation.id} icon={Deny} label="Block" color="danger" />
          </div>
        </div>
        <BidsRow bids={donation.bids} />
      </div>
      <div className={styles.comment}>
        <Highlighter
          highlightClassName={styles.highlighted}
          searchWords={keywords}
          textToHighlight={donation.comment || ''}
        />
      </div>
    </div>
  );
}
