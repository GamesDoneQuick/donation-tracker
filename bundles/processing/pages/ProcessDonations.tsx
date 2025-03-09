import React from 'react';
import { useQuery, UseQueryResult } from 'react-query';
import { Button, Header, openModal, Stack } from '@faulty/gdq-design';

import APIClient from '@public/apiv2/APIClient';
import type { APIDonation as Donation, APIEvent as Event } from '@public/apiv2/APITypes';
import { usePermission } from '@public/apiv2/helpers/auth';
import { useEventParam } from '@public/apiv2/hooks';
import Title from '@public/Title';
import Plus from '@uikit/icons/Plus';

import CreateEditDonationGroupModal from '@processing/modules/donation-groups/CreateEditDonationGroupModal';
import useDonationGroupsStore from '@processing/modules/donation-groups/DonationGroupsStore';
import FilterGroupTab, { FilterGroupTabDropTarget } from '@processing/modules/reading/FilterGroupTab';
import { FILTER_ITEMS, FilterGroupTabItem } from '@processing/modules/reading/ReadingTypes';

import DonationList from '../modules/donations/DonationList';
import { DonationState, loadDonations, useDonationsInState } from '../modules/donations/DonationsStore';
import SearchKeywordsInput from '../modules/donations/SearchKeywordsInput';
import SidebarLayout from '../modules/layout/SidebarLayout';
import ActionLog from '../modules/processing/ActionLog';
import ConnectionStatus from '../modules/processing/ConnectionStatus';
import ProcessingDonationRow from '../modules/processing/ProcessingDonationRow';
import ProcessingModeSelector from '../modules/processing/ProcessingModeSelector';
import ProcessingPartitionSettings from '../modules/processing/ProcessingPartitionSettings';
import useProcessingStore, { ProcessingMode } from '../modules/processing/ProcessingStore';
import { ProcessDefinition } from '../modules/processing/ProcessingTypes';
import { useGroupItems } from './useGroupItems';

import styles from '@processing/pages/ReadDonations.mod.css';

const PROCESSES: Record<ProcessingMode, ProcessDefinition> = {
  flag: {
    donationState: 'unprocessed',
    fetch: (eventId: number) => APIClient.getUnprocessedDonations(eventId),
    action: (donationId: number) => APIClient.flagDonation(donationId),
    actionName: 'Sent to Head',
    actionLabel: 'Send to Head',
  },
  confirm: {
    donationState: 'flagged',
    fetch: (eventId: number) => APIClient.getFlaggedDonations(eventId),
    action: (donationId: number) => APIClient.sendDonationToReader(donationId),
    actionName: 'Sent to Reader',
    actionLabel: 'Send to Reader',
  },
  onestep: {
    donationState: 'unprocessed',
    fetch: (eventId: number) => APIClient.getUnprocessedDonations(eventId),
    action: (donationId: number) => APIClient.sendDonationToReader(donationId),
    actionName: 'Sent to Reader',
    actionLabel: 'Send to Reader',
  },
};

interface SidebarProps {
  event: Event | undefined;
  donationsQuery: UseQueryResult<Donation[]>;
  groupItems: FilterGroupTabItem[];
  selectedTabId: string;
  onTabSelect: (item: FilterGroupTabItem) => unknown;
}

const stateMap: Record<ProcessingMode, DonationState> = {
  flag: 'ready',
  onestep: 'ready',
  confirm: 'flagged',
};

function Sidebar(props: SidebarProps) {
  const { event, donationsQuery, groupItems, selectedTabId, onTabSelect } = props;

  const handleCreateGroup = React.useCallback(() => {
    openModal(props => <CreateEditDonationGroupModal {...props} />);
  }, []);

  const handleEditGroup = React.useCallback((item: FilterGroupTabItem) => {
    if (item.type !== 'group') return;

    const group = useDonationGroupsStore.getState().groups.find(group => group.id === item.id);
    openModal(modalProps => <CreateEditDonationGroupModal group={group} {...modalProps} />);
  }, []);

  const { processingMode, setProcessingMode } = useProcessingStore();
  const canAddGroups = usePermission('tracker.add_donationgroup');
  const canSendToReader = usePermission('tracker.send_to_reader');
  const canSelectModes = canSendToReader && !event?.use_one_step_screening;

  // TODO: pull this logic out into a helper
  React.useEffect(() => {
    if (event?.use_one_step_screening) {
      setProcessingMode('onestep');
    } else if (event) {
      if (
        (!event.use_one_step_screening && processingMode === 'onestep') ||
        (processingMode === 'confirm' && !canSelectModes)
      ) {
        setProcessingMode('flag');
      }
    }
  }, [event, setProcessingMode, processingMode, canSelectModes]);

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
          <ProcessingModeSelector initialMode={processingMode} onSelect={handleApprovalModeChanged} />
        ) : null}
        <ProcessingPartitionSettings />
        <SearchKeywordsInput />
        {(processingMode === 'onestep' || processingMode === 'confirm') && (
          <>
            {FILTER_ITEMS.slice(0, 1).map(item => (
              <FilterGroupTab
                key={item.id}
                item={item}
                donationState={stateMap[processingMode]}
                isSelected={selectedTabId === item.id}
                onSelected={onTabSelect}
              />
            ))}
            <Header tag="h3" variant="header-sm/normal" className={styles.header}>
              <div className={styles.groupsHeader}>
                <span className={styles.groupsHeaderTitle}>Custom Groups</span>
                {/* eslint-disable-next-line react/jsx-no-bind */}
                {canAddGroups && <Button variant="link/filled" icon={() => <Plus />} onPress={handleCreateGroup} />}
              </div>
            </Header>
            {groupItems.map(item => (
              <FilterGroupTab
                key={item.id}
                item={item}
                donationState={stateMap[processingMode]}
                isSelected={selectedTabId === item.id}
                onEdit={handleEditGroup}
                onSelected={onTabSelect}
              />
            ))}
            <FilterGroupTabDropTarget />
          </>
        )}
      </Stack>
      <ActionLog />
    </Stack>
  );
}

export default function ProcessDonations() {
  const eventId = useEventParam();

  const { partition, partitionCount, processingMode } = useProcessingStore();
  const process = PROCESSES[processingMode];

  const { data: event } = useQuery(`events.${eventId}`, () => APIClient.getEvent(eventId));
  const donationsQuery = useQuery(`donations.unprocessed.${processingMode}`, () => process.fetch(eventId), {
    onSuccess: donations => loadDonations(donations),
  });

  const groupItems = useGroupItems(donationsQuery);

  const partitionFilter = React.useCallback(
    (donation: Donation) => {
      return donation.id % partitionCount === partition;
    },
    [partition, partitionCount],
  );

  const donations = useDonationsInState(process.donationState, partitionFilter);

  const [selectedTab, setSelectedTab] = React.useState<FilterGroupTabItem>(FILTER_ITEMS[0]);

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
      sidebar={
        <Sidebar
          event={event}
          donationsQuery={donationsQuery}
          groupItems={groupItems}
          selectedTabId={selectedTab.id}
          onTabSelect={setSelectedTab}
        />
      }>
      <Title>{event?.name}</Title>
      <DonationList
        isLoading={donationsQuery.isLoading}
        isError={donationsQuery.isError}
        donations={donations}
        renderDonationRow={renderDonationRow}
      />
    </SidebarLayout>
  );
}
