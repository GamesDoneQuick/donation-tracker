import * as React from 'react';
import classNames from 'classnames';
import { useMutation, UseMutationResult, useQuery } from 'react-query';
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
import Refresh from '@uikit/icons/Refresh';
import SendForward from '@uikit/icons/SendForward';

import getEstimatedReadingTime from './getEstimatedReadingTIme';
import useProcessingStore, { HistoryAction, useUnprocessedDonations } from './ProcessingStore';
import { AdminRoutes, useAdminRoute } from './Routes';

import styles from './Processing.mod.css';

const REFETCH_INTERVAL = 2 * 60 * 1000; // 2 minutes

type ApprovalMode = 'flag' | 'approve';

function useDonationMutation(mutation: (donationId: number) => Promise<Donation>, actionLabel: string) {
  const store = useProcessingStore();
  return useMutation(mutation, {
    onSuccess: (donation: Donation) => store.processDonation(donation, actionLabel),
  });
}

const BUTTON_COLOR_STYLES = {
  success: styles.buttonSuccess,
  danger: styles.buttonDanger,
  default: styles.buttonDefault,
  warning: styles.buttonWarning,
  info: styles.buttonInfo,
};

interface MutationButtonProps<T> {
  mutation: UseMutationResult<T, unknown, number, unknown>;
  donationId: number;
  color?: keyof typeof BUTTON_COLOR_STYLES;
  label: React.ReactNode;
  icon?: React.ComponentType;
  disabled?: boolean;
}

function MutationButton<T>(props: MutationButtonProps<T>) {
  const { mutation, donationId, color = 'default', label, icon: Icon, disabled = false } = props;

  return (
    <button
      className={classNames(styles.actionButton, BUTTON_COLOR_STYLES[color])}
      onClick={() => mutation.mutate(donationId)}
      disabled={disabled || mutation.isLoading}>
      {/* @ts-expect-error Icons have bad typing from fontawesome */}
      {Icon != null ? <Icon className={styles.actionButtonIcon} /> : null} {label}
    </button>
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
  approvalMode: ApprovalMode;
}

function DonationRow(props: DonationRowProps) {
  const { donation, approvalMode } = props;
  const timestamp = TimeUtils.parseTimestamp(donation.timereceived);

  const donationLink = useAdminRoute(AdminRoutes.DONATION(donation.id));
  const donorLink = useAdminRoute(AdminRoutes.DONOR(donation.donor));
  const canEditDonors = usePermission('tracker.change_donor');

  const approve = useDonationMutation(
    (donationId: number) => APIClient.approveDonationComment(`${donationId}`),
    'approved',
  );
  const deny = useDonationMutation((donationId: number) => APIClient.denyDonationComment(`${donationId}`), 'blocked');
  const flag = useDonationMutation((donationId: number) => APIClient.flagDonation(`${donationId}`), 'flagged');
  const sendToReader = useDonationMutation(
    (donationId: number) => APIClient.sendDonationToReader(`${donationId}`),
    'sent to reader',
  );

  const donorName = canEditDonors ? <a href={donorLink}>{donation.donor_name}</a> : <p>{donation.donor_name}</p>;
  const donationAmount = <a href={donationLink}>{CurrencyUtils.asCurrency(donation.amount)}</a>;
  const readingTime = getEstimatedReadingTime(donation.comment);

  const approvalButton = (function () {
    switch (approvalMode) {
      case 'flag':
        return (
          <MutationButton
            mutation={flag}
            donationId={donation.id}
            icon={SendForward}
            label="Send to Head"
            color="success"
          />
        );
      case 'approve':
        return (
          <MutationButton
            mutation={sendToReader}
            donationId={donation.id}
            icon={SendForward}
            label="Send to Reader"
            color="success"
          />
        );
    }
  })();

  return (
    <div className={styles.donation}>
      <div className={styles.donationHeader}>
        <div className={styles.donationTopHeader}>
          <p className={styles.donationTitle}>
            <span className={styles.donationTitleHeader}>
              <strong>{donationAmount}</strong> from <strong>{donorName}</strong>
            </span>
            <span className={styles.donationTimestamp}>Received at {timestamp.toFormat('hh:mma')}</span>
            <span className={styles.expectedReadingTime}>Reading time: {readingTime}</span>
          </p>
          <div className={styles.donationActionRow}>
            {approvalButton}
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

function ActionEntry({ action }: { action: HistoryAction }) {
  const donationLink = useAdminRoute(AdminRoutes.DONATION(action.donationId));
  const donation = useProcessingStore(state => state.donations[action.donationId]);

  return (
    <div className={styles.historyAction} key={action.id}>
      {action.label} <a href={donationLink}>{CurrencyUtils.asCurrency(donation.amount)}</a> from {donation.donor_name}
    </div>
  );
}

function ActionLog() {
  const history = useProcessingStore(state => state.actionHistory.slice(0, 20));

  return (
    <div className={styles.sidebarHistory}>
      <h5>Action History</h5>
      {history.map(action => (
        <ActionEntry key={action.id} action={action} />
      ))}
    </div>
  );
}

function AutoRefresher({ refetch, isFetching }: { refetch: () => Promise<unknown>; isFetching: boolean }) {
  const [lastRefresh, setLastRefresh] = React.useState(() => Date.now());
  const [, forceUpdate] = React.useState({});

  const handleRefetch = React.useCallback(() => {
    refetch().then(() => setLastRefresh(Date.now()));
  }, [refetch]);

  React.useEffect(() => {
    const interval = setInterval(handleRefetch, REFETCH_INTERVAL);
    return () => clearInterval(interval);
  }, [handleRefetch]);

  React.useEffect(() => {
    function updateTimer() {
      forceUpdate({});
      requestAnimationFrame(updateTimer);
    }

    const rAF = requestAnimationFrame(updateTimer);
    return () => cancelAnimationFrame(rAF);
  });

  const elapsedInterval = Date.now() - lastRefresh;
  const intervalPercentage = (elapsedInterval / REFETCH_INTERVAL) * 100;

  return (
    <div className={styles.autoRefresher}>
      <div className={styles.refreshProgress}>
        <div className={styles.refreshProgressBar} style={{ width: `${intervalPercentage}%` }} />
      </div>
      <button className={styles.actionButton} onClick={handleRefetch}>
        {isFetching ? (
          <>
            <Spinner /> Loading
          </>
        ) : (
          <>
            <Refresh className={styles.actionButtonIcon} /> Refresh Now
          </>
        )}
      </button>
    </div>
  );
}

export default function ProcessDonations() {
  const params = useParams<{ eventId: string }>();
  const { eventId } = params;

  const { partition, partitionCount, loadDonations, setPartition, setPartitionCount } = useProcessingStore();

  const { data: event } = useQuery(`events.${eventId}`, () => APIClient.getEvent(eventId));
  const donationsQuery = useQuery('donations.unprocessed', () => APIClient.getUnprocessedDonations(eventId), {
    onSuccess: donations => loadDonations(donations),
  });

  const unprocessedDonations = useUnprocessedDonations();
  const [approvalMode, setApprovalMode] = React.useState<ApprovalMode>('flag');
  const canSendToReader = usePermission('tracker.send_to_reader');
  const canSelectModes = canSendToReader && !event?.use_one_step_screening;

  React.useEffect(() => {
    if (event?.use_one_step_screening) {
      setApprovalMode('approve');
    }
  }, [event, canSendToReader]);

  function handleApprovalModeChanged(event: React.ChangeEvent<HTMLSelectElement>) {
    if (!canSendToReader) return;

    setApprovalMode(event.target.value as ApprovalMode);
  }

  if (donationsQuery.isLoading && !donationsQuery.isFetched) return <Spinner />;
  if (donationsQuery.isError) return <div>Failed to load donations {JSON.stringify(donationsQuery.error)}</div>;

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
        <TransitionGroup>
          {unprocessedDonations
            ?.filter(donation => donation.id % partitionCount === partition)
            .map(donation => (
              <CSSTransition
                key={donation.id}
                timeout={150}
                classNames={{ exit: styles.donationExit, exitActive: styles.donationExitActive }}>
                <DonationRow donation={donation} approvalMode={approvalMode} />
              </CSSTransition>
            ))}
        </TransitionGroup>
        <div className={styles.endOfList}>You&apos;ve reached the end of your current donation list.</div>
      </main>
    </div>
  );
}
