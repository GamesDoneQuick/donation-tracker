import * as React from 'react';
import classNames from 'classnames';
import { useDrag, useDrop } from 'react-dnd';
import Highlighter from 'react-highlight-words';
import { useMutation, useQuery } from 'react-query';
import { useParams } from 'react-router';
import { CSSTransition, TransitionGroup } from 'react-transition-group';
import {
  Anchor,
  Button,
  Card,
  Checkbox,
  Clickable,
  Header,
  openModal,
  openPopout,
  Spacer,
  Stack,
  TabColor,
  Tabs,
  Tag,
  Text,
  useHoverFocus,
  useTooltip,
} from '@spyrothon/sparx';

import { usePermission } from '@public/api/helpers/auth';
import APIClient from '@public/apiv2/APIClient';
import type { Donation } from '@public/apiv2/APITypes';
import * as CurrencyUtils from '@public/util/currency';
import TimeUtils from '@public/util/TimeUtils';
import Approve from '@uikit/icons/Approve';
import Deny from '@uikit/icons/Deny';
import Dots from '@uikit/icons/Dots';
import DragHandle from '@uikit/icons/DragHandle';
import Plus from '@uikit/icons/Plus';

import ConnectionStatus from './ConnectionStatus';
import CreateEditDonationGroupModal from './CreateEditDonationGroupModal';
import useDonationGroupsStore, {
  DonationGroup,
  moveDonationWithinGroup,
  useGroupsForDonation,
} from './DonationGroupsStore';
import useDonationsStore, { loadDonations, useDonation, useDonations, useDonationsInState } from './DonationsStore';
import getEstimatedReadingTime from './getEstimatedReadingTIme';
import MutationButton from './MutationButton';
import ProcessingSidebar from './ProcessingSidebar';
import RelativeTime from './RelativeTime';
import { AdminRoutes, useAdminRoute } from './Routes';
import SearchKeywordsInput from './SearchKeywordsInput';
import { useSearchKeywords } from './SearchKeywordsStore';

import donationStyles from './DonationRow.mod.css';
import styles from './Processing.mod.css';

interface AddToGroupPopoutProps {
  donationId: number;
}

function AddToGroupPopout(props: AddToGroupPopoutProps) {
  const { donationId } = props;
  const donation = useDonation(donationId);
  const { groups, addDonationToGroup, removeDonationFromGroup, removeDonationFromAllGroups } = useDonationGroupsStore();

  const amount = CurrencyUtils.asCurrency(donation.amount);
  const donationLink = useAdminRoute(AdminRoutes.DONATION(donation.id));
  const donorLink = useAdminRoute(AdminRoutes.DONOR(donation.donor));
  const canEditDonors = usePermission('tracker.change_donor');

  const pin = useMutation(() => APIClient.pinDonation(`${donation.id}`), {
    onSuccess: donation => loadDonations([donation]),
  });
  const unpin = useMutation(() => APIClient.unpinDonation(`${donation.id}`), {
    onSuccess: donation => loadDonations([donation]),
  });
  const block = useMutation(() => APIClient.denyDonationComment(`${donation.id}`), {
    onSuccess: donation => {
      loadDonations([donation]);
      removeDonationFromAllGroups(donation.id);
    },
  });

  function handlePinChange() {
    donation.pinned ? unpin.mutate() : pin.mutate();
  }

  function handleBlock() {
    block.mutate();
  }

  return (
    <Card floating>
      <Stack>
        <div>
          <Header tag="h1" variant="header-sm/normal">
            {amount} from {donation.donor_name}
          </Header>
          <Text variant="text-sm/secondary">
            #{donation.id}
            {' · '}
            <Anchor href={donationLink} newTab>
              Edit Donation
            </Anchor>
            {canEditDonors ? (
              <>
                {' · '}
                <Anchor href={donorLink} newTab>
                  Edit Donor
                </Anchor>
              </>
            ) : null}
          </Text>
        </div>
        <Spacer />
        <Checkbox label="Pin for Everyone" checked={donation.pinned} onChange={handlePinChange} />
        <Header tag="h2" variant="header-sm/normal">
          Add to Groups
        </Header>
        {groups.map(group => {
          const isIncluded = group.donationIds.includes(donation.id);
          function handleGroupChange() {
            isIncluded ? removeDonationFromGroup(group.id, donation.id) : addDonationToGroup(group.id, donation.id);
          }
          return <Checkbox key={group.id} label={group.name} checked={isIncluded} onChange={handleGroupChange} />;
        })}
        <Spacer size="space-md" />
        <Button variant="danger/outline" onClick={handleBlock}>
          Block
        </Button>
      </Stack>
    </Card>
  );
}

interface DonationRowProps {
  donation: Donation;
  draggable: boolean;
  currentGroupId: DonationGroup['id'];
}

function DonationRow(props: DonationRowProps) {
  const { donation, draggable, currentGroupId } = props;
  const timestamp = TimeUtils.parseTimestamp(donation.timereceived);
  const searchKeywords = useSearchKeywords();

  const readingTime = getEstimatedReadingTime(donation.comment);
  const amount = CurrencyUtils.asCurrency(donation.amount);
  const hasComment = donation.comment != null && donation.comment.length > 0;

  const removeDonationFromAllGroups = useDonationGroupsStore(state => state.removeDonationFromAllGroups);
  const groups = useGroupsForDonation(donation.id);
  const [moreActionsTooltipProps] = useTooltip<HTMLButtonElement>('More Actions');

  const read = useMutation((donationId: number) => APIClient.readDonation(`${donationId}`), {
    onSuccess: (donation: Donation) => {
      loadDonations([donation]);
      removeDonationFromAllGroups(donation.id);
    },
  });
  const ignore = useMutation((donationId: number) => APIClient.ignoreDonation(`${donationId}`), {
    onSuccess: (donation: Donation) => {
      loadDonations([donation]);
      removeDonationFromAllGroups(donation.id);
    },
  });

  const donationRef = React.useRef<HTMLDivElement>(null);
  const [{ isDragging }, drag, preview] = useDrag(() => ({
    type: 'donation',
    item: donation,
    collect: monitor => ({ isDragging: monitor.isDragging() }),
  }));
  const [{ isOver, canDrop }, drop] = useDrop(() => ({
    accept: ['donation'],
    drop(item: Donation) {
      moveDonationWithinGroup(currentGroupId, item.id, donation.id);
    },
    canDrop(item: Donation) {
      return item.id !== donation.id;
    },
    collect: monitor => ({
      isOver: monitor.isOver(),
      canDrop: monitor.canDrop(),
    }),
  }));
  drop(preview(donationRef.current));

  function handleMoreActions(event: React.MouseEvent) {
    openPopout(() => <AddToGroupPopout donationId={donation.id} />, event.currentTarget as HTMLElement);
  }

  return (
    <div
      className={classNames(donationStyles.container, {
        [donationStyles.isDropOver]: isOver && canDrop,
        [donationStyles.dragging]: isDragging,
      })}
      ref={donationRef}>
      <div className={donationStyles.dropIndicator} />
      <div className={donationStyles.header}>
        <Stack direction="horizontal" justify="space-between" align="center" className={donationStyles.headerTop}>
          <Stack direction="horizontal" align="center" spacing="space-lg">
            {draggable ? (
              <Text variant="text-md/normal">
                <Clickable ref={drag} className={styles.donationDragHandle} aria-label="Drag Donation">
                  <DragHandle />
                </Clickable>
              </Text>
            ) : null}
            <Stack spacing="space-none">
              <Text variant="text-md/normal">
                <strong>{amount}</strong>
                {' from '}
                <strong>
                  <Highlighter
                    searchWords={searchKeywords}
                    textToHighlight={donation.donor_name}
                    highlightClassName={donationStyles.highlighted}></Highlighter>
                </strong>
              </Text>
              <Stack direction="horizontal" spacing="space-sm" align="center">
                {groups.map(group => (
                  <Tag key={group.id} color={group.color}>
                    {group.name}
                  </Tag>
                ))}
                {groups.length > 0 ? ' · ' : null}
                <Text variant="text-sm/normal">
                  <span>
                    <RelativeTime time={timestamp.toJSDate()} />
                  </span>
                  {' · '}
                  {readingTime} to read
                </Text>
              </Stack>
            </Stack>
          </Stack>
          <Stack direction="horizontal">
            <MutationButton
              mutation={read}
              donationId={donation.id}
              icon={Approve}
              label="Mark as Read"
              variant="success"
            />
            <MutationButton
              mutation={ignore}
              donationId={donation.id}
              icon={Deny}
              label="Mark as Ignored"
              variant="danger"
            />
            <Button {...moreActionsTooltipProps} onClick={handleMoreActions} variant="default">
              <Dots />
            </Button>
          </Stack>
        </Stack>
      </div>

      <Text
        variant={hasComment ? 'text-md/normal' : 'text-md/secondary'}
        className={classNames(donationStyles.comment, { [donationStyles.noCommentHint]: !hasComment })}>
        {hasComment ? (
          <Highlighter
            highlightClassName={donationStyles.highlighted}
            searchWords={searchKeywords}
            textToHighlight={donation.comment || ''}
          />
        ) : (
          'No comment was provided'
        )}
      </Text>
    </div>
  );
}

interface DonationDropTargetProps {
  currentGroupId: DonationGroup['id'];
  lastDonationId: Donation['id'];
}

function DonationDropTarget(props: DonationDropTargetProps) {
  const { currentGroupId, lastDonationId } = props;

  const [{ isOver, canDrop }, drop] = useDrop(
    () => ({
      accept: ['donation'],
      drop(item: Donation) {
        moveDonationWithinGroup(currentGroupId, item.id, lastDonationId, true);
      },
      canDrop(item: Donation) {
        return item.id !== lastDonationId;
      },
      collect(monitor) {
        return {
          isOver: monitor.isOver(),
          canDrop: monitor.canDrop(),
        };
      },
    }),
    [lastDonationId],
  );

  return (
    <div
      ref={drop}
      className={classNames(donationStyles.emptyDropTarget, { [donationStyles.isDropOver]: isOver && canDrop })}>
      <div className={donationStyles.dropIndicator} />
    </div>
  );
}

interface DonationListProps {
  donationIds: Set<number> | number[];
  allowReordering: boolean;
  currentGroupId: DonationGroup['id'];
}

function DonationList(props: DonationListProps) {
  const { donationIds, allowReordering, currentGroupId } = props;
  const donations = useDonations(donationIds);

  return (
    <>
      <TransitionGroup>
        {donations.map(donation => (
          <CSSTransition
            key={donation.id}
            timeout={240}
            classNames={{
              enter: styles.donationEnter,
              enterActive: styles.donationEnterActive,
              exit: styles.donationExit,
              exitActive: styles.donationExitActive,
            }}>
            <DonationRow donation={donation} currentGroupId={currentGroupId} draggable={allowReordering} />
          </CSSTransition>
        ))}
        {allowReordering && donations.length > 0 ? (
          <DonationDropTarget currentGroupId={currentGroupId} lastDonationId={donations[donations.length - 1].id} />
        ) : null}
      </TransitionGroup>
    </>
  );
}

function CreateGroupButton() {
  function handleClick() {
    openModal(props => <CreateEditDonationGroupModal {...props} />);
  }

  return <Button variant="link/filled" icon={Plus} onClick={handleClick} />;
}

function useFilteredDonationGroups(donations: Donation[]) {
  function noCommentDonationFilter(donation: Donation) {
    return donation.comment == null || donation.comment.length === 0;
  }

  function pinnedDonationFilter(donation: Donation) {
    return donation.pinned;
  }

  // TODO(faulty): Better represent anonymous donations so they actually have a
  // flag instead of having to check the name like this.
  function anonymousDonationFilter(donation: Donation) {
    return donation.donor_name === '(Anonymous)' || donation.donor_name === '';
  }

  return React.useMemo(() => {
    const noCommentDonationIds = [];
    const pinnedDonationIds = [];
    const anonymousDonationIds = [];

    for (const donation of donations) {
      if (noCommentDonationFilter(donation)) noCommentDonationIds.push(donation.id);
      if (pinnedDonationFilter(donation)) pinnedDonationIds.push(donation.id);
      if (anonymousDonationFilter(donation)) anonymousDonationIds.push(donation.id);
    }

    return { noCommentDonationIds, pinnedDonationIds, anonymousDonationIds };
  }, [donations]);
}

interface FilterGroupItem {
  id: string;
  label: string;
  count: number;
  color: TabColor;
  donationIds: number[];
  group?: DonationGroup;
}

interface FilterGroupTabProps {
  item: FilterGroupItem;
  isSelected: boolean;
  onSelected: (name: string) => void;
}

function FilterGroupTab(props: FilterGroupTabProps) {
  const { item, isSelected, onSelected } = props;

  const [hoverFocusProps, active] = useHoverFocus();

  function handleSelect() {
    onSelected(item.id);
  }

  function handleEdit(event: React.MouseEvent) {
    event.stopPropagation();
    openModal(modalProps => <CreateEditDonationGroupModal group={item.group} {...modalProps} />);
  }

  return (
    <Tabs.Tab
      key={item.label}
      label={item.label}
      color={item.color}
      onClick={handleSelect}
      selected={isSelected}
      badge={
        <Stack direction="horizontal" spacing="space-lg">
          {item.group != null && active ? (
            <Clickable onClick={handleEdit}>
              <Dots />
            </Clickable>
          ) : null}
          {item.count}
        </Stack>
      }
      {...hoverFocusProps}
    />
  );
}

export default function ReadDonations() {
  const params = useParams<{ eventId: string }>();
  const { eventId } = params;

  const { data: event } = useQuery(`events.${eventId}`, () => APIClient.getEvent(eventId));
  const donationsQuery = useQuery(`donations.unread`, () => APIClient.getUnreadDonations(eventId), {
    onSuccess: loadDonations,
  });

  const groups = useDonationGroupsStore(state => state.groups);
  const donations = useDonationsInState('ready');
  const { noCommentDonationIds, pinnedDonationIds, anonymousDonationIds } = useFilteredDonationGroups(donations);

  const filterTabItems: FilterGroupItem[] = [
    {
      id: 'all',
      label: 'All Donations',
      count: donations.length,
      donationIds: donations.map(donation => donation.id),
      color: 'default',
    },
    {
      id: 'no-comment',
      label: 'No Comment',
      count: noCommentDonationIds.length,
      donationIds: noCommentDonationIds,
      color: 'default',
    },
    {
      id: 'anonymous',
      label: 'Anonymous',
      count: anonymousDonationIds.length,
      donationIds: anonymousDonationIds,
      color: 'default',
    },
    {
      id: 'pinned',
      label: 'Pinned',
      count: pinnedDonationIds.length,
      donationIds: pinnedDonationIds,
      color: 'default',
    },
  ];

  const groupTabItems: FilterGroupItem[] = groups.map(group => ({
    id: group.id,
    label: group.name,
    count: group.donationIds.length,
    color: group.color,
    donationIds: group.donationIds,
    group,
  }));
  const [selectedGroupId, setSelectedGroupId] = React.useState<string>(filterTabItems[0].id);
  const selectedGroup =
    filterTabItems.find(tab => tab.id === selectedGroupId) ||
    groupTabItems.find(tab => tab.id === selectedGroupId) ||
    filterTabItems[0];

  // When the page first loads, force a refresh of all donations that have been
  // saved into groups to ensure they are present and up-to-date, then filter
  // out any donations that were in groups but have since been processed.
  React.useEffect(() => {
    (async () => {
      const { groups, removeDonationFromAllGroups } = useDonationGroupsStore.getState();
      const ids = new Set<number>();
      for (const group of Object.values(groups)) {
        group.donationIds.forEach(id => ids.add(id));
      }
      const donations = await APIClient.getDonations(Array.from(ids).map(String));
      loadDonations(donations);

      const { ready } = useDonationsStore.getState();
      for (const id of ids) {
        if (!ready.has(id)) {
          removeDonationFromAllGroups(id);
        }
      }
    })();
  }, []);

  return (
    <div className={styles.container}>
      <ProcessingSidebar event={event} subtitle="Read Donations" className={styles.sidebar}>
        <ConnectionStatus refetch={donationsQuery.refetch} isFetching={donationsQuery.isRefetching} />
        <SearchKeywordsInput />
        <Tabs.Group>
          <Tabs.Header label="Filters" />
          {filterTabItems.map(tab => (
            <FilterGroupTab
              key={tab.label}
              item={tab}
              isSelected={selectedGroupId === tab.id}
              onSelected={setSelectedGroupId}
            />
          ))}
          <Tabs.Header
            label={
              <div className={styles.groupsHeader}>
                <span className={styles.groupsHeaderTitle}>Custom Groups</span>
                <CreateGroupButton />
              </div>
            }
          />
          {groupTabItems.map(tab => (
            <FilterGroupTab
              key={tab.label}
              item={tab}
              isSelected={selectedGroupId === tab.id}
              onSelected={setSelectedGroupId}
            />
          ))}
        </Tabs.Group>
      </ProcessingSidebar>
      <main className={styles.main}>
        <DonationList
          key={selectedGroupId}
          donationIds={selectedGroup.donationIds}
          // Filters cannot be reordered since they are not finite, only
          // defined Groups support ordering.
          allowReordering={selectedGroup.group != null}
          currentGroupId={selectedGroupId}
        />
      </main>
    </div>
  );
}
