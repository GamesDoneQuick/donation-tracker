import React from 'react';
import { useQuery, UseQueryResult } from 'react-query';
import { Button, Header, openModal, Stack } from '@faulty/gdq-design';

import APIClient from '@public/apiv2/APIClient';
import { APIDonation as Donation } from '@public/apiv2/APITypes';
import { usePermission } from '@public/apiv2/helpers/auth';
import { useEventParam } from '@public/apiv2/hooks';
import Plus from '@uikit/icons/Plus';

import DonationDropTarget from '@processing/modules/donations/DonationDropTarget';
import DonationList from '@processing/modules/donations/DonationList';
import FilterGroupTab, { FilterGroupTabDropTarget } from '@processing/modules/reading/FilterGroupTab';
import ReadingDonationRow from '@processing/modules/reading/ReadingDonationRow';
import { FILTER_ITEMS, FilterGroupTabItem, GroupTabItem } from '@processing/modules/reading/ReadingTypes';
import useDonationsForFilterGroupTab from '@processing/modules/reading/useDonationsForFilterGroupTab';
import { useGroupItems } from '@processing/pages/useGroupItems';

import CreateEditDonationGroupModal from '../modules/donation-groups/CreateEditDonationGroupModal';
import useDonationGroupsStore, {
  DonationGroup,
  moveDonationWithinGroup,
} from '../modules/donation-groups/DonationGroupsStore';
import { loadDonations } from '../modules/donations/DonationsStore';
import SearchKeywordsInput from '../modules/donations/SearchKeywordsInput';
import SidebarLayout from '../modules/layout/SidebarLayout';
import ConnectionStatus from '../modules/processing/ConnectionStatus';

import styles from './ReadDonations.mod.css';

const READING_DONATION_STATE = 'ready';

interface EndOfGroupDropTargetProps {
  groupId: DonationGroup['id'];
  lastDonationId: Donation['id'];
}

function EndOfGroupDropTarget(props: EndOfGroupDropTargetProps) {
  const { groupId, lastDonationId } = props;
  const onDrop = React.useCallback(
    (item: Donation) => {
      moveDonationWithinGroup(groupId, item.id, lastDonationId, true);
    },
    [groupId, lastDonationId],
  );

  const canDrop = React.useCallback((item: Donation) => item.id !== lastDonationId, [lastDonationId]);

  return <DonationDropTarget onDrop={onDrop} canDrop={canDrop} />;
}

function ScrollToBottomButton({ onPress }: { onPress: () => void }) {
  return (
    <div className={styles.scrollToBottomContainer}>
      <Button className={styles.scrollToBottomButton} variant="info/filled" onPress={onPress}>
        Jump to Bottom
      </Button>
    </div>
  );
}

interface SidebarProps {
  donationsQuery: UseQueryResult<Donation[]>;
  groupItems: GroupTabItem[];
  selectedTabId: string;
  onTabSelect: (item: FilterGroupTabItem) => unknown;
}

function Sidebar(props: SidebarProps) {
  const { donationsQuery, groupItems, selectedTabId, onTabSelect } = props;

  const handleCreateGroup = React.useCallback(() => {
    openModal(props => <CreateEditDonationGroupModal {...props} />);
  }, []);

  const canAddGroups = usePermission('tracker.add_donationgroup');

  const handleEditGroup = React.useCallback((item: FilterGroupTabItem) => {
    if (item.type !== 'group') return;

    const group = useDonationGroupsStore.getState().groups.find(group => group.id === item.id);
    openModal(modalProps => <CreateEditDonationGroupModal group={group} {...modalProps} />);
  }, []);

  return (
    <Stack spacing="space-xl">
      <ConnectionStatus refetch={donationsQuery.refetch} isFetching={donationsQuery.isRefetching} />
      <SearchKeywordsInput />
      <Stack spacing="space-xs">
        <Header tag="h3" variant="header-sm/normal" className={styles.header}>
          Filters
        </Header>
        {FILTER_ITEMS.map(item => (
          <FilterGroupTab
            key={item.id}
            item={item}
            donationState={READING_DONATION_STATE}
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
            donationState={READING_DONATION_STATE}
            isSelected={selectedTabId === item.id}
            onEdit={handleEditGroup}
            onSelected={onTabSelect}
          />
        ))}
        <FilterGroupTabDropTarget />
      </Stack>
    </Stack>
  );
}

export default function ReadDonations() {
  const eventId = useEventParam();

  const { data: event } = useQuery(`events.${eventId}`, () => APIClient.getEvent(eventId));
  const donationsQuery = useQuery(`donations.unread`, () => APIClient.getUnreadDonations(eventId), {
    onSuccess: loadDonations,
  });
  const groupItems = useGroupItems(donationsQuery);

  const [selectedTab, setSelectedTab] = React.useState<FilterGroupTabItem>(FILTER_ITEMS[0]);
  const tabDonations = useDonationsForFilterGroupTab(selectedTab, READING_DONATION_STATE);
  // Filters cannot be reordered since they are not finite, only
  // defined Groups support ordering.
  const allowReordering = selectedTab.type === 'group';

  React.useEffect(() => {
    const validTabIds = [...FILTER_ITEMS, ...groupItems].map(item => item.id);
    if (!validTabIds.includes(selectedTab.id)) {
      setSelectedTab(FILTER_ITEMS[0]);
    }
  }, [groupItems, selectedTab]);

  const renderDonationRow = React.useCallback(
    (donation: Donation) => (
      <ReadingDonationRow donation={donation} currentGroupId={selectedTab.id} draggable={allowReordering} />
    ),
    [allowReordering, selectedTab],
  );

  const mainRef = React.useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = React.useState(false);
  const isAtBottomRef = React.useRef(false);

  React.useLayoutEffect(() => {
    const main = mainRef.current;
    if (main == null) return;

    function onScroll() {
      const main = mainRef.current;
      if (main == null) return;

      const isAtBottom = main.clientHeight + main.scrollTop >= main.scrollHeight - 100;
      if (isAtBottomRef.current !== isAtBottom) {
        setIsAtBottom(isAtBottom);
      }
      isAtBottomRef.current = isAtBottom;
    }

    main.addEventListener('scroll', onScroll);
    return () => main.removeEventListener('scroll', onScroll);
  }, []);

  const scrollToBottom = React.useCallback(() => {
    const main = mainRef.current;
    if (main == null) return;

    main.scrollTo({ top: main.scrollHeight });
  }, []);

  return (
    <SidebarLayout
      event={event}
      subtitle="Read Donations"
      sidebar={
        <Sidebar
          donationsQuery={donationsQuery}
          groupItems={groupItems}
          selectedTabId={selectedTab.id}
          onTabSelect={setSelectedTab}
        />
      }
      mainClassName={styles.main}>
      {!isAtBottom ? <ScrollToBottomButton onPress={scrollToBottom} /> : null}
      <div className={styles.scroller} ref={mainRef}>
        <DonationList
          isError={donationsQuery.isError}
          isLoading={donationsQuery.isLoading}
          key={selectedTab.id}
          donations={tabDonations}
          renderDonationRow={renderDonationRow}
        />
        {allowReordering && selectedTab.type === 'group' && tabDonations.length > 0 ? (
          <EndOfGroupDropTarget groupId={selectedTab.id} lastDonationId={tabDonations[tabDonations.length - 1].id} />
        ) : null}
      </div>
    </SidebarLayout>
  );
}
