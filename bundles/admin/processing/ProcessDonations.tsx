import * as React from 'react';
import { useMutation, UseMutationResult, useQuery, UseQueryResult } from 'react-query';
import { useParams } from 'react-router';
import { CSSTransition, TransitionGroup } from 'react-transition-group';

import { usePermission } from '@public/api/helpers/auth';
import APIClient from '@public/apiv2/APIClient';
import type { Donation, DonationBid } from '@public/apiv2/APITypes';
import Spinner from '@public/spinner';
import * as CurrencyUtils from '@public/util/currency';
import TimeUtils from '@public/util/TimeUtils';
import Approve from '@uikit/icons/Approve';
import Deny from '@uikit/icons/Deny';
import SendForward from '@uikit/icons/SendForward';

import ActionLog from './ActionLog';
import AutoRefresher from './AutoRefresher';
import Button from './Button';
import getEstimatedReadingTime from './getEstimatedReadingTIme';
import useProcessingStore, { ApprovalMode, useUnprocessedDonations } from './ProcessingStore';
import { AdminRoutes, useAdminRoute } from './Routes';

import styles from './Processing.mod.css';

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

  return <div className={styles.donationBidsRow}>Attached Bids: {bidNames.join(' • ')}</div>;
}

interface DonationRowProps {
  donation: Donation;
  process: ProcessDefinition;
}

function DonationRow(props: DonationRowProps) {
  const { donation, process } = props;
  const timestamp = TimeUtils.parseTimestamp(donation.timereceived);

  const donationLink = useAdminRoute(AdminRoutes.DONATION(donation.id));
  const donorLink = useAdminRoute(AdminRoutes.DONOR(donation.donor));
  const canEditDonors = usePermission('tracker.change_donor');

  const action = useDonationMutation((donationId: number) => process.action(`${donationId}`), process.actionName);
  const approve = useDonationMutation(
    (donationId: number) => APIClient.approveDonationComment(`${donationId}`),
    'Approved',
  );
  const deny = useDonationMutation((donationId: number) => APIClient.denyDonationComment(`${donationId}`), 'Blocked');

  const donorName =
    canEditDonors && donation.donor != null ? (
      <a href={donorLink} target="_blank" rel="noreferrer">
        {donation.donor_name}
      </a>
    ) : (
      <span>{donation.donor_name}</span>
    );
  const readingTime = getEstimatedReadingTime(donation.comment);

  return (
    <div className={styles.donation}>
      <div className={styles.donationHeader}>
        <div className={styles.donationTopHeader}>
          <div className={styles.donationTitle}>
            <div className={styles.donationTitleHeader}>
              <strong>{CurrencyUtils.asCurrency(donation.amount)}</strong> from <strong>{donorName}</strong>
            </div>
            <div className={styles.donationTitleByline}>
              <span className={styles.donationId}>
                <a href={donationLink} target="_blank" rel="noreferrer">
                  #{donation.id}
                </a>
              </span>
              {' – '}
              <span className={styles.donationTimestamp}>Received at {timestamp.toFormat('hh:mma')}</span>
              {' – '}
              <span className={styles.expectedReadingTime}>Reading time: {readingTime}</span>
            </div>
          </div>
          <div className={styles.donationActionRow}>
            <MutationButton
              mutation={action}
              donationId={donation.id}
              icon={SendForward}
              color="success"
              label={process.actionLabel}
            />
            <MutationButton mutation={approve} donationId={donation.id} icon={Approve} label="Approve Only" />
            <MutationButton mutation={deny} donationId={donation.id} icon={Deny} label="Block" color="danger" />
          </div>
        </div>
        <BidsRow bids={donation.bids} />
      </div>
      <div className={styles.donationComment}>
        <span>{donation.comment}</span>
      </div>
    </div>
  );
}

interface DonationListProps {
  query: UseQueryResult;
  process: ProcessDefinition;
}

function DonationList(props: DonationListProps) {
  const { query, process } = props;
  const unprocessedDonations = useUnprocessedDonations();

  if (query.isLoading) {
    return (
      <div className={styles.endOfList}>
        <Spinner />
      </div>
    );
  }

  if (query.isError) {
    return <div className={styles.endOfList}>Failed to load donations {JSON.stringify(query.error)}</div>;
  }

  return (
    <>
      <TransitionGroup>
        {unprocessedDonations.map(donation => (
          <CSSTransition
            key={donation.id}
            timeout={240}
            classNames={{ exit: styles.donationExit, exitActive: styles.donationExitActive }}>
            <DonationRow donation={donation} process={process} />
          </CSSTransition>
        ))}
      </TransitionGroup>
      <div className={styles.endOfList}>
        {query.isFetching ? `Loading donations...` : `You've reached the end of your current donation list.`}
      </div>
    </>
  );
}

interface InputProps {
  label: string;
  children: React.ReactNode;
}

function Input(props: InputProps) {
  const { label, children } = props;

  return (
    <div className={styles.input}>
      <label>{label}</label>
      {children}
    </div>
  );
}

interface ProcessDefinition {
  fetch: (eventId: string) => Promise<Donation[]>;
  action: (donationId: string) => Promise<Donation>;
  actionName: string;
  actionLabel: string;
}

const PROCESSES: Record<ApprovalMode, ProcessDefinition> = {
  flag: {
    fetch: (eventId: string) => APIClient.getUnprocessedDonations(eventId),
    action: (donationId: string) => APIClient.flagDonation(donationId),
    actionName: 'Sent to Head',
    actionLabel: 'Send to Head',
  },
  approve: {
    fetch: (eventId: string) => APIClient.getFlaggedDonations(eventId),
    action: (donationId: string) => APIClient.sendDonationToReader(donationId),
    actionName: 'Sent to Reader',
    actionLabel: 'Send to Reader',
  },
};

export default function ProcessDonations() {
  const params = useParams<{ eventId: string }>();
  const { eventId } = params;

  const {
    approvalMode,
    partition,
    partitionCount,
    loadDonations,
    setApprovalMode,
    setPartition,
    setPartitionCount,
  } = useProcessingStore();

  const process = PROCESSES[approvalMode];

  const { data: event } = useQuery(`events.${eventId}`, () => APIClient.getEvent(eventId));
  const donationsQuery = useQuery(`donations.unprocessed.${approvalMode}`, () => process.fetch(eventId), {
    onSuccess: donations => loadDonations(donations),
  });

  const canSendToReader = usePermission('tracker.send_to_reader');
  const canSelectModes = canSendToReader && !event?.use_one_step_screening;

  React.useEffect(() => {
    if (event?.use_one_step_screening) {
      setApprovalMode('approve');
    }
  }, [event, setApprovalMode, canSendToReader]);

  function handleApprovalModeChanged(event: React.ChangeEvent<HTMLSelectElement>) {
    if (!canSendToReader) return;

    setApprovalMode(event.target.value as ApprovalMode);
  }

  return (
    <div className={styles.container}>
      <div className={styles.sidebar}>
        <h4 className={styles.eventName}>{event?.name}</h4>
        <div className={styles.sidebarFilters}>
          {canSelectModes ? (
            <Input label="Processing Mode">
              <select
                name="processing-mode"
                data-test-id="processing-mode"
                onChange={handleApprovalModeChanged}
                value={approvalMode}>
                <option value="flag">Regular</option>
                <option value="approve">Confirm</option>
              </select>
            </Input>
          ) : null}
          <Input label="Partition ID">
            <input
              type="number"
              min="0"
              max={partitionCount - 1}
              value={partition}
              onChange={e => setPartition(+e.target.value)}
            />
          </Input>
          <Input label="Partition Count">
            <input type="number" min="1" value={partitionCount} onChange={e => setPartitionCount(+e.target.value)} />
          </Input>
        </div>
        <AutoRefresher refetch={donationsQuery.refetch} isFetching={donationsQuery.isRefetching} />
        <ActionLog />
      </div>
      <main className={styles.main}>
        <DonationList query={donationsQuery} process={process} />
      </main>
    </div>
  );
}
