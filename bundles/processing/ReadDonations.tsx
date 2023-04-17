import * as React from 'react';
import classNames from 'classnames';
import { useMutation, useQuery } from 'react-query';
import { useParams } from 'react-router';
import { CSSTransition, TransitionGroup } from 'react-transition-group';
import {
  Anchor,
  Button,
  Card,
  Checkbox,
  Header,
  openModal,
  openPopout,
  Spacer,
  Stack,
  TabColor,
  Tabs,
  Tag,
  Text,
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
import Plus from '@uikit/icons/Plus';

import ConnectionStatus from './ConnectionStatus';
import CreateEditDonationGroupModal from './CreateEditDonationGroupModal';
import useDonationGroupsStore, { useGroupsForDonation } from './DonationGroupsStore';
import { loadDonations, useDonation, useDonations, useDonationsInState } from './DonationsStore';
import getEstimatedReadingTime from './getEstimatedReadingTIme';
import MutationButton from './MutationButton';
import ProcessingSidebar from './ProcessingSidebar';
import { AdminRoutes, useAdminRoute } from './Routes';

import donationStyles from './DonationRow.mod.css';
import styles from './Processing.mod.css';

interface AddToGroupPopoutProps {
  donationId: number;
}

function AddToGroupPopout(props: AddToGroupPopoutProps) {
  const { donationId } = props;
  const donation = useDonation(donationId);
  const { groups, addDonationToGroup, removeDonationFromGroup } = useDonationGroupsStore();

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

  function handlePinChange() {
    donation.pinned ? unpin.mutate() : pin.mutate();
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
            isIncluded ? removeDonationFromGroup(group.name, donation.id) : addDonationToGroup(group.name, donation.id);
          }
          return <Checkbox key={group.name} label={group.name} checked={isIncluded} onChange={handleGroupChange} />;
        })}
      </Stack>
    </Card>
  );
}

interface DonationRowProps {
  donation: Donation;
}

function DonationRow(props: DonationRowProps) {
  const { donation } = props;
  const timestamp = TimeUtils.parseTimestamp(donation.timereceived);

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

  function handleMoreActions(event: React.MouseEvent) {
    openPopout(() => <AddToGroupPopout donationId={donation.id} />, event.currentTarget as HTMLElement);
  }

  return (
    <div className={donationStyles.container}>
      <div className={donationStyles.header}>
        <Stack direction="horizontal" justify="space-between" align="center" className={donationStyles.headerTop}>
          <Stack spacing="space-sm">
            <Text variant="text-md/normal">
              <strong>{amount}</strong>
              {' from '}
              <strong>{donation.donor_name}</strong>
            </Text>
            <Stack direction="horizontal" spacing="space-sm" align="center">
              {groups.map(group => (
                <Tag key={group.name} color={group.color}>
                  {group.name}
                </Tag>
              ))}
              {groups.length > 0 ? ' · ' : null}
              <Text variant="text-sm/normal">
                <span>{timestamp.toFormat('yyyy-MM-dd hh:mm:ss a')}</span>
                {' · '}
                {readingTime} to read
              </Text>
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
        {hasComment ? donation.comment : 'No comment was provided'}
      </Text>
    </div>
  );
}

interface DonationListProps {
  donationIds: Set<number> | number[];
}

function DonationList(props: DonationListProps) {
  const { donationIds } = props;
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
            <DonationRow donation={donation} />
          </CSSTransition>
        ))}
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
  label: string;
  count: number;
  color: TabColor;
  donationIds: number[];
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
      label: 'All Donations',
      count: donations.length,
      donationIds: donations.map(donation => donation.id),
      color: 'default',
    },
    {
      label: 'No Comment',
      count: noCommentDonationIds.length,
      donationIds: noCommentDonationIds,
      color: 'default',
    },
    {
      label: 'Anonymous',
      count: anonymousDonationIds.length,
      donationIds: anonymousDonationIds,
      color: 'default',
    },
    {
      label: 'Pinned',
      count: pinnedDonationIds.length,
      donationIds: pinnedDonationIds,
      color: 'default',
    },
  ];

  const groupTabItems: FilterGroupItem[] = groups.map(group => ({
    label: group.name,
    count: group.donationIds.length,
    color: group.color,
    donationIds: group.donationIds,
  }));
  const [selectedGroupName, setSelectedGroupName] = React.useState<string>(filterTabItems[0].label);
  const selectedGroup =
    filterTabItems.find(tab => tab.label === selectedGroupName) ||
    groupTabItems.find(tab => tab.label === selectedGroupName) ||
    filterTabItems[0];

  // When the page first loads, force a refresh of all donations that have been
  // saved into groups to ensure they are present and up-to-date.
  React.useEffect(() => {
    (async () => {
      const { groups } = useDonationGroupsStore.getState();
      const ids = new Set<string>();
      for (const group of Object.values(groups)) {
        group.donationIds.forEach(id => ids.add(String(id)));
      }
      const donations = await APIClient.getDonations(Array.from(ids));
      loadDonations(donations);
    })();
  }, []);

  function getGroupSelectHandler(groupName: string) {
    return () => setSelectedGroupName(groupName);
  }

  return (
    <div className={styles.container}>
      <ProcessingSidebar event={event} subtitle="Read Donations" className={styles.sidebar}>
        <ConnectionStatus refetch={donationsQuery.refetch} isFetching={donationsQuery.isRefetching} />
        <Tabs.Group>
          <Tabs.Header label="Filters" />
          {filterTabItems.map(tab => (
            <Tabs.Tab
              key={tab.label}
              label={tab.label}
              color={tab.color}
              onClick={getGroupSelectHandler(tab.label)}
              selected={selectedGroupName === tab.label}
              badge={tab.count}
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
            <Tabs.Tab
              key={tab.label}
              label={tab.label}
              color={tab.color}
              onClick={getGroupSelectHandler(tab.label)}
              selected={selectedGroupName === tab.label}
              badge={tab.count}
            />
          ))}
        </Tabs.Group>
      </ProcessingSidebar>
      <main className={styles.main}>
        <DonationList key={selectedGroupName} donationIds={selectedGroup.donationIds} />
      </main>
    </div>
  );
}
