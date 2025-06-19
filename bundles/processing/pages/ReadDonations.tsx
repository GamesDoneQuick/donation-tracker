import React from 'react';
import { Button, Header, openModal, Stack } from '@faulty/gdq-design';

import { useDonationsInState, usePermission } from '@public/apiv2/hooks';
import { Donation } from '@public/apiv2/Models';
import EventTitle from '@public/EventTitle';
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
import SearchKeywordsInput from '../modules/donations/SearchKeywordsInput';
import SidebarLayout from '../modules/layout/SidebarLayout';
import ConnectionStatus from '../modules/processing/ConnectionStatus';

import styles from './ReadDonations.mod.css';

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
  refetch: () => unknown;
  isFetching: boolean;
  groupItems: GroupTabItem[];
  selectedTabId: string;
  onTabSelect: (item: FilterGroupTabItem) => unknown;
}

function Sidebar(props: SidebarProps) {
  const { refetch, isFetching, groupItems, selectedTabId, onTabSelect } = props;

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
      <ConnectionStatus refetch={refetch} isFetching={isFetching} />
      <SearchKeywordsInput />
      <Stack spacing="space-xs">
        <Header tag="h3" variant="header-sm/normal" className={styles.header}>
          Filters
        </Header>
        {FILTER_ITEMS.map(item => (
          <FilterGroupTab
            key={item.id}
            item={item}
            donationState="unread"
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
            donationState="unread"
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
  const [selectedTab, setSelectedTab] = React.useState<FilterGroupTabItem>(FILTER_ITEMS[0]);
  const { data: donations, isLoading, isError, isFetching, refetch } = useDonationsInState('unread');
  const { data: tabDonations } = useDonationsForFilterGroupTab(selectedTab, 'unread');
  const groupItems = useGroupItems(donations);
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
      subtitle="Read Donations"
      sidebar={
        <Sidebar
          refetch={refetch}
          isFetching={isFetching}
          groupItems={groupItems}
          selectedTabId={selectedTab.id}
          onTabSelect={setSelectedTab}
        />
      }
      mainClassName={styles.main}>
      <EventTitle>Read Donations</EventTitle>
      {!isAtBottom ? <ScrollToBottomButton onPress={scrollToBottom} /> : null}
      <div className={styles.scroller} ref={mainRef}>
        <DonationList
          isError={isError}
          isLoading={isLoading}
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
