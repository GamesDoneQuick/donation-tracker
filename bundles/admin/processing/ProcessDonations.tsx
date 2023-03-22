import * as React from 'react';
import { useQuery, UseQueryResult } from 'react-query';
import { useParams } from 'react-router';
import { CSSTransition, TransitionGroup } from 'react-transition-group';

import { usePermission } from '@public/api/helpers/auth';
import APIClient from '@public/apiv2/APIClient';
import type { Donation } from '@public/apiv2/APITypes';
import Spinner from '@public/spinner';

import ActionLog from './ActionLog';
import ConnectionStatus from './ConnectionStatus';
import DonationRow from './DonationRow';
import Input from './Input';
import useProcessingStore, { ProcessingMode, useUnprocessedDonations } from './ProcessingStore';
import { ThemeButton } from './Theming';

import styles from './Processing.mod.css';

interface ProcessDefinition {
  fetch: (eventId: string) => Promise<Donation[]>;
  action: (donationId: string) => Promise<Donation>;
  actionName: string;
  actionLabel: string;
}

const PROCESSES: Record<ProcessingMode, ProcessDefinition> = {
  flag: {
    fetch: (eventId: string) => APIClient.getUnprocessedDonations(eventId),
    action: (donationId: string) => APIClient.flagDonation(donationId),
    actionName: 'Sent to Head',
    actionLabel: 'Send to Head',
  },
  confirm: {
    fetch: (eventId: string) => APIClient.getFlaggedDonations(eventId),
    action: (donationId: string) => APIClient.sendDonationToReader(donationId),
    actionName: 'Sent to Reader',
    actionLabel: 'Send to Reader',
  },
  onestep: {
    fetch: (eventId: string) => APIClient.getUnprocessedDonations(eventId),
    action: (donationId: string) => APIClient.sendDonationToReader(donationId),
    actionName: 'Sent to Reader',
    actionLabel: 'Send to Reader',
  },
};

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
            classNames={{
              enter: styles.donationEnter,
              enterActive: styles.donationEnterActive,
              exit: styles.donationExit,
              exitActive: styles.donationExitActive,
            }}>
            <DonationRow
              donation={donation}
              action={process.action}
              actionLabel={process.actionLabel}
              actionName={process.actionName}
            />
          </CSSTransition>
        ))}
      </TransitionGroup>
      <div className={styles.endOfList}>
        {query.isFetching ? `Loading donations...` : `You've reached the end of your current donation list.`}
      </div>
    </>
  );
}

export default function ProcessDonations() {
  const params = useParams<{ eventId: string }>();
  const { eventId } = params;

  const {
    partition,
    partitionCount,
    loadDonations,
    processingMode,
    setProcessingMode,
    setPartition,
    setPartitionCount,
    setKeywords,
  } = useProcessingStore();

  const process = PROCESSES[processingMode];

  const { data: event } = useQuery(`events.${eventId}`, () => APIClient.getEvent(eventId));
  const donationsQuery = useQuery(`donations.unprocessed.${processingMode}`, () => process.fetch(eventId), {
    onSuccess: donations => loadDonations(donations),
  });

  const canSendToReader = usePermission('tracker.send_to_reader');
  const canSelectModes = canSendToReader && !event?.use_one_step_screening;

  React.useEffect(() => {
    if (event?.use_one_step_screening) {
      setProcessingMode('onestep');
    }
  }, [event, setProcessingMode, canSendToReader]);

  function handleApprovalModeChanged(event: React.ChangeEvent<HTMLSelectElement>) {
    if (!canSendToReader) return;

    setProcessingMode(event.target.value as ProcessingMode);
  }

  function handleKeywordsChange(event: React.ChangeEvent<HTMLTextAreaElement>) {
    const words = event.target.value.split(',').map(word => `\\b${word.trim()}\\b`);
    setKeywords(words);
  }

  return (
    <div className={styles.container}>
      <div className={styles.sidebar}>
        <h4 className={styles.eventName}>{event?.name}</h4>
        <div className={styles.sidebarFilters}>
          <ThemeButton className={styles.themeButton} />
          {canSelectModes ? (
            <Input label="Processing Mode">
              <select
                name="processing-mode"
                data-test-id="processing-mode"
                onChange={handleApprovalModeChanged}
                value={processingMode}>
                <option value="flag">Regular</option>
                <option value="confirm">Confirm</option>
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
          <Input label="Keywords" note="Comma-separated list of words or phrases to highlight in donations">
            <textarea rows={2} onChange={handleKeywordsChange} />
          </Input>
        </div>
        <ConnectionStatus refetch={donationsQuery.refetch} isFetching={donationsQuery.isRefetching} />
        <ActionLog />
      </div>
      <main className={styles.main}>
        <DonationList query={donationsQuery} process={process} />
      </main>
    </div>
  );
}
