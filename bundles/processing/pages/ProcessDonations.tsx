import * as React from 'react';
import { useQuery, UseQueryResult } from 'react-query';
import { useParams } from 'react-router';
import { FormControl, Stack } from '@spyrothon/sparx';

import { usePermission } from '@public/api/helpers/auth';
import APIClient from '@public/apiv2/APIClient';
import type { Donation, Event } from '@public/apiv2/APITypes';

import DonationList from '../modules/donations/DonationList';
import { loadDonations, useDonationsInState } from '../modules/donations/DonationsStore';
import SearchKeywordsInput from '../modules/donations/SearchKeywordsInput';
import SidebarLayout from '../modules/layout/SidebarLayout';
import ActionLog from '../modules/processing/ActionLog';
import ConnectionStatus from '../modules/processing/ConnectionStatus';
import ProcessingDonationRow from '../modules/processing/ProcessingDonationRow';
import ProcessingModeSelector from '../modules/processing/ProcessingModeSelector';
import ProcessingPartitionSettings from '../modules/processing/ProcessingPartitionSettings';
import useProcessingStore, { ProcessingMode } from '../modules/processing/ProcessingStore';
import { ProcessDefinition } from '../modules/processing/ProcessingTypes';

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

interface SidebarProps {
  event: Event | undefined;
  donationsQuery: UseQueryResult<Donation[]>;
}

function Sidebar(props: SidebarProps) {
  const { event, donationsQuery } = props;

  const { processingMode, setProcessingMode } = useProcessingStore();
  const canSendToReader = usePermission('tracker.send_to_reader');
  const canSelectModes = canSendToReader && !event?.use_one_step_screening;

  React.useEffect(() => {
    if (event?.use_one_step_screening) {
      setProcessingMode('onestep');
    } else if (event && !event.use_one_step_screening && processingMode === 'onestep') {
      setProcessingMode('flag');
    }
  }, [event, setProcessingMode, processingMode]);

  const handleApprovalModeChanged = React.useCallback(
    (mode: ProcessingMode) => {
      if (!canSendToReader || mode == null) return;

      setProcessingMode(mode);
    },
    [canSendToReader, setProcessingMode],
  );

  return (
    <Stack spacing="space-xl">
      <ConnectionStatus refetch={donationsQuery.refetch} isFetching={donationsQuery.isRefetching} />
      <Stack>
        {canSelectModes ? (
          <FormControl label="Processing Mode">
            <ProcessingModeSelector initialMode={processingMode} onSelect={handleApprovalModeChanged} />
          </FormControl>
        ) : null}
        <ProcessingPartitionSettings />
        <SearchKeywordsInput />
      </Stack>
      <ActionLog />
    </Stack>
  );
}

export default function ProcessDonations() {
  const params = useParams<{ eventId: string }>();
  const { eventId } = params;

  const { partition, partitionCount, processingMode } = useProcessingStore();
  const process = PROCESSES[processingMode];

  const { data: event } = useQuery(`events.${eventId}`, () => APIClient.getEvent(eventId!));
  const donationsQuery = useQuery(`donations.unprocessed.${processingMode}`, () => process.fetch(eventId!), {
    onSuccess: donations => loadDonations(donations),
  });

  const partitionFilter = React.useCallback(
    (donation: Donation) => {
      return donation.id % partitionCount === partition;
    },
    [partition, partitionCount],
  );

  const donations = useDonationsInState(process.donationState, partitionFilter);

  const renderDonationRow = React.useCallback(
    (donation: Donation) => (
      <ProcessingDonationRow
        donation={donation}
        action={process.action}
        actionLabel={process.actionLabel}
        actionName={process.actionName}
      />
    ),
    [process],
  );

  return (
    <SidebarLayout
      event={event}
      subtitle="Donation Processing"
      sidebar={<Sidebar event={event} donationsQuery={donationsQuery} />}>
      <DonationList
        isLoading={donationsQuery.isLoading}
        isError={donationsQuery.isError}
        donations={donations}
        renderDonationRow={renderDonationRow}
      />
    </SidebarLayout>
  );
}
