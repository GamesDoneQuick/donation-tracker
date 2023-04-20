import * as React from 'react';
import { useQuery, UseQueryResult } from 'react-query';
import { useParams } from 'react-router';
import { CSSTransition, TransitionGroup } from 'react-transition-group';
import { FormControl, SelectInput, Stack, Text, TextArea, TextInput } from '@spyrothon/sparx';

import { usePermission } from '@public/api/helpers/auth';
import APIClient from '@public/apiv2/APIClient';
import type { Donation } from '@public/apiv2/APITypes';
import Spinner from '@public/spinner';

import ActionLog from './ActionLog';
import ConnectionStatus from './ConnectionStatus';
import DonationRow from './DonationRow';
import { DonationState, loadDonations, useDonationsInState } from './DonationsStore';
import ProcessingSidebar from './ProcessingSidebar';
import useProcessingStore, { ProcessingMode } from './ProcessingStore';
import { setSearchKeywords, useSearchKeywords } from './SearchKeywordsStore';

import styles from './Processing.mod.css';

interface ProcessDefinition {
  donationState: DonationState;
  fetch: (eventId: string) => Promise<Donation[]>;
  action: (donationId: string) => Promise<Donation>;
  actionName: string;
  actionLabel: string;
}

const PROCESSES: Record<ProcessingMode, ProcessDefinition> = {
  flag: {
    donationState: 'unprocessed',
    fetch: (eventId: string) => APIClient.getUnprocessedDonations(eventId),
    action: (donationId: string) => APIClient.flagDonation(donationId),
    actionName: 'Sent to Head',
    actionLabel: 'Send to Head',
  },
  confirm: {
    donationState: 'flagged',
    fetch: (eventId: string) => APIClient.getFlaggedDonations(eventId),
    action: (donationId: string) => APIClient.sendDonationToReader(donationId),
    actionName: 'Sent to Reader',
    actionLabel: 'Send to Reader',
  },
  onestep: {
    donationState: 'unprocessed',
    fetch: (eventId: string) => APIClient.getUnprocessedDonations(eventId),
    action: (donationId: string) => APIClient.sendDonationToReader(donationId),
    actionName: 'Sent to Reader',
    actionLabel: 'Send to Reader',
  },
};

interface DonationListProps {
  donationState: DonationState;
  query: UseQueryResult;
  process: ProcessDefinition;
}

function DonationList(props: DonationListProps) {
  const { donationState, query, process } = props;
  const unprocessedDonations = useDonationsInState(donationState);

  if (query.isLoading) {
    return (
      <div className={styles.endOfList}>
        <Spinner />
      </div>
    );
  }

  if (query.isError) {
    return <Text className={styles.endOfList}>Failed to load donations: {JSON.stringify(query.error)}</Text>;
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
      <Text className={styles.endOfList}>
        {query.isFetching ? `Loading donations...` : `You've reached the end of your current donation list.`}
      </Text>
    </>
  );
}

interface ProcessingModeSelectorProps {
  initialMode: ProcessingMode;
  onSelect: (mode: ProcessingMode) => unknown;
}

function ProcessingModeSelector(props: ProcessingModeSelectorProps) {
  const { onSelect, initialMode } = props;

  const PROCESSING_MODE_ITEMS = [
    {
      name: 'Regular',
      value: 'flag',
    },
    {
      name: 'Confirm',
      value: 'confirm',
    },
  ];

  type ModeSelectItem = typeof PROCESSING_MODE_ITEMS[number];

  const [selectedMode, setSelectedMode] = React.useState<ModeSelectItem | undefined>(() =>
    PROCESSING_MODE_ITEMS.find(mode => mode.value === initialMode),
  );

  function handleSelect(item: ModeSelectItem | undefined) {
    if (item == null) return;

    setSelectedMode(item);
    onSelect(item.value as ProcessingMode);
  }

  return <SelectInput items={PROCESSING_MODE_ITEMS} onSelect={handleSelect} selectedItem={selectedMode} />;
}

export default function ProcessDonations() {
  const params = useParams<{ eventId: string }>();
  const { eventId } = params;

  const {
    partition,
    setPartition,
    partitionCount,
    setPartitionCount,
    processingMode,
    setProcessingMode,
  } = useProcessingStore();

  const searchKeywords = useSearchKeywords();

  // Keywords are stored as a split array with some additional formatting. To
  // pre-fill the input from local storage on page load, we need to un-format
  // and re-join the words back into a regular string.
  const [initialKeywords] = React.useState(() => searchKeywords.map(word => word.replace(/\\b/g, '')).join(', '));

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

  function handleApprovalModeChanged(mode: ProcessingMode) {
    if (!canSendToReader || mode == null) return;

    setProcessingMode(mode);
  }

  function handleKeywordsChange(event: React.ChangeEvent<HTMLTextAreaElement>) {
    const words = event.target.value.split(',').map(word => `\\b${word.trim()}\\b`);
    setSearchKeywords(words);
  }

  return (
    <div className={styles.container}>
      <ProcessingSidebar event={event} subtitle="Donation Processing" className={styles.sidebar}>
        <Stack>
          {canSelectModes ? (
            <FormControl label="Processing Mode">
              <ProcessingModeSelector initialMode={processingMode} onSelect={handleApprovalModeChanged} />
            </FormControl>
          ) : null}
          <Stack className={styles.partitionSelector} direction="horizontal" wrap={false} justify="stretch">
            <FormControl label="Partition ID">
              <TextInput
                type="number"
                min={1}
                max={partitionCount}
                value={partition + 1}
                // eslint-disable-next-line react/jsx-no-bind
                onChange={e => setPartition(+e.target.value - 1)}
              />
            </FormControl>
            <FormControl label="Partition Count">
              <TextInput
                type="number"
                min="1"
                value={partitionCount}
                // eslint-disable-next-line react/jsx-no-bind
                onChange={e => setPartitionCount(+e.target.value)}
              />
            </FormControl>
          </Stack>
          <FormControl label="Keywords" note="Comma-separated list of words or phrases to highlight in donations">
            <TextArea rows={2} defaultValue={initialKeywords} onChange={handleKeywordsChange} />
          </FormControl>
        </Stack>
        <ConnectionStatus refetch={donationsQuery.refetch} isFetching={donationsQuery.isRefetching} />
        <ActionLog />
      </ProcessingSidebar>
      <main className={styles.main}>
        <DonationList donationState={process.donationState} query={donationsQuery} process={process} />
      </main>
    </div>
  );
}
