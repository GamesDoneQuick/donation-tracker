import React from 'react';
import { useNavigate } from 'react-router';
import { Button, Header, openModal, Stack } from '@faulty/gdq-design';

import {
  useEventFromRoute,
  useFlagDonationMutation,
  usePermission,
  useSendDonationToReaderMutation,
} from '@public/apiv2/hooks';
import { Donation } from '@public/apiv2/Models';
import { DonationState } from '@public/apiv2/reducers/trackerApi';
import EventTitle from '@public/EventTitle';
import Plus from '@uikit/icons/Plus';

import CreateEditDonationGroupModal from '@processing/modules/donation-groups/CreateEditDonationGroupModal';
import useDonationGroupsStore from '@processing/modules/donation-groups/DonationGroupsStore';
import FilterGroupTab, { FilterGroupTabDropTarget } from '@processing/modules/reading/FilterGroupTab';
import { FILTER_ITEMS, FilterGroupTabItem } from '@processing/modules/reading/ReadingTypes';
import useDonationsForFilterGroupTab from '@processing/modules/reading/useDonationsForFilterGroupTab';

import DonationList from '../modules/donations/DonationList';
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
    useAction: useFlagDonationMutation,
    actionName: 'Sent to Head',
    actionLabel: 'Send to Head',
  },
  confirm: {
    donationState: 'flagged',
    useAction: useSendDonationToReaderMutation,
    actionName: 'Sent to Reader',
    actionLabel: 'Send to Reader',
  },
  onestep: {
    donationState: 'unprocessed',
    useAction: useSendDonationToReaderMutation,
    actionName: 'Sent to Reader',
    actionLabel: 'Send to Reader',
  },
};

interface SidebarProps {
  refetch: () => unknown;
  isFetching: boolean;
  groupItems: FilterGroupTabItem[];
  selectedTabId: string;
  onTabSelect: (item: FilterGroupTabItem) => unknown;
}

const stateMap: Record<ProcessingMode, DonationState> = {
  flag: 'unread',
  onestep: 'unread',
  confirm: 'flagged',
};

function Sidebar(props: SidebarProps) {
  const { refetch, isFetching, groupItems, selectedTabId, onTabSelect } = props;
  const { data: event } = useEventFromRoute();

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
  const canSelectModes = canSendToReader && event?.screening_mode === 'two_pass';

  // TODO: pull this logic out into a helper
  React.useEffect(() => {
    if (event) {
      if (event.screening_mode !== 'two_pass') {
        setProcessingMode('onestep');
      } else if (
        (event.screening_mode === 'two_pass' && processingMode === 'onestep') ||
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
      <ConnectionStatus refetch={refetch} isFetching={isFetching} />
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
  const { partition, partitionCount, processingMode } = useProcessingStore();
  const process = PROCESSES[processingMode];
  const { data: event } = useEventFromRoute();
  const navigate = useNavigate();

  const [selectedTab, setSelectedTab] = React.useState<FilterGroupTabItem>(FILTER_ITEMS[0]);
  const {
    data: tabDonations,
    refetch,
    isLoading,
    isError,
    isFetching,
  } = useDonationsForFilterGroupTab(selectedTab, process.donationState);
  const donations = React.useMemo(
    () => tabDonations.filter(donation => donation.id % partitionCount === partition),
    [partition, partitionCount, tabDonations],
  );
  const groupItems = useGroupItems(donations);

  const renderDonationRow = React.useCallback(
    (donation: Donation) => (
      <ProcessingDonationRow
        donation={donation}
        useAction={process.useAction}
        actionLabel={process.actionLabel}
        actionName={process.actionName}
      />
    ),
    [process],
  );

  if (event?.screening_mode === 'host_only') {
    navigate(`/v2/${event.id}/processing/read`);
    return <React.Fragment />;
  }

  return (
    <SidebarLayout
      subtitle="Donation Processing"
      sidebar={
        <Sidebar
          refetch={refetch}
          isFetching={isFetching}
          groupItems={groupItems}
          selectedTabId={selectedTab.id}
          onTabSelect={setSelectedTab}
        />
      }>
      <EventTitle>Process Donations</EventTitle>
      <DonationList
        isLoading={isLoading}
        isError={isError}
        donations={donations}
        renderDonationRow={renderDonationRow}
      />
    </SidebarLayout>
  );
}
