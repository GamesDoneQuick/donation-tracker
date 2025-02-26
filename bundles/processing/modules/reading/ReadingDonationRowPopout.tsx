import React from 'react';
import { DateTime } from 'luxon';
import { Anchor, Button, Card, Checkbox, Header, openModal, Spacer, Stack, Text } from '@faulty/gdq-design';

import APIErrorList from '@public/APIErrorList';
import {
  useAddDonationToGroupMutation,
  useDenyDonationCommentMutation,
  useDonation,
  usePermission,
  usePinDonationMutation,
  useRemoveDonationFromGroupMutation,
  useUnpinDonationMutation,
} from '@public/apiv2/hooks';
import { Donation } from '@public/apiv2/Models';
import { useCachedCallback } from '@public/hooks/useCachedCallback';
import * as CurrencyUtils from '@public/util/currency';

import ModCommentModal from '@processing/modules/donations/ModCommentModal';
import { AdminRoutes, useAdminRoute } from '@processing/Routes';

import useDonationGroupsStore, { DonationGroup } from '../donation-groups/DonationGroupsStore';

interface ReadingDonationRowPopoutProps {
  donationId: number;
  showBlock: boolean;
  showGroups: boolean;
  showPin: boolean;
  onClose: () => void;
}

function DonationGroupCheckbox({
  group,
  donation,
  toggle,
  disabled,
}: {
  group: DonationGroup;
  donation: Donation;
  toggle: () => void;
  disabled: boolean;
}) {
  const isIncluded = donation.groups?.includes(group.id) || false;
  return <Checkbox isDisabled={disabled} label={group.name} checked={isIncluded} onChange={toggle} />;
}

export default function ReadingDonationRowPopout(props: ReadingDonationRowPopoutProps) {
  const { donationId, onClose, showBlock, showGroups, showPin } = props;
  const { data } = useDonation(donationId);
  const { groups } = useDonationGroupsStore();

  // fake it for layout purposes
  const fake = React.useMemo<Donation>(
    () => ({
      type: 'donation',
      id: 0,
      donor_name: '(unknown)',
      event: 0,
      domain: 'LOCAL',
      commentstate: 'PENDING',
      readstate: 'PENDING',
      transactionstate: 'COMPLETED',
      amount: 0,
      currency: 'usd',
      timereceived: DateTime.now(),
      commentlanguage: 'un',
      pinned: false,
      bids: [],
    }),
    [],
  );

  const donation = data ?? fake;

  const donationLink = useAdminRoute(AdminRoutes.DONATION(donation.id));
  const donorLink = useAdminRoute(AdminRoutes.DONOR(donation.donor));
  const canEditDonors = usePermission('tracker.change_donor');

  const [pin, pinResult] = usePinDonationMutation();
  const [unpin, unpinResult] = useUnpinDonationMutation();
  const [block, blockResult] = useDenyDonationCommentMutation();
  const [addToGroup, addResult] = useAddDonationToGroupMutation();
  const [removeFromGroup, removeResult] = useRemoveDonationFromGroupMutation();
  const toggleGroup = React.useCallback(
    (group: string) => {
      const isIncluded = donation.groups?.includes(group) ?? false;
      (isIncluded ? removeFromGroup : addToGroup)({ donationId: donation.id, group });
    },
    [addToGroup, donation, removeFromGroup],
  );

  const handlePinChange = React.useCallback(() => {
    (donation.pinned ? unpin : pin)(donation.id);
  }, [donation, pin, unpin]);

  const handleToggleGroup = useCachedCallback(
    (group: string) => {
      toggleGroup(group);
    },
    [toggleGroup],
  );

  const handleBlock = React.useCallback(async () => {
    const { data } = await block(donation.id);
    if (data) {
      onClose();
    }
  }, [block, donation, onClose]);

  const handleEditModComment = React.useCallback(() => {
    onClose();
    openModal(props => <ModCommentModal donation={donation} {...props} />);
  }, [donation, onClose]);

  const amount = CurrencyUtils.asCurrency(donation.amount, { currency: donation.currency });

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
            {canEditDonors && donation.donor ? (
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
        {showPin && (
          <>
            <Checkbox
              label="Pin for Everyone"
              isDisabled={pinResult.isLoading || unpinResult.isLoading}
              checked={donation.pinned}
              onChange={handlePinChange}
            />
            <APIErrorList errors={[pinResult.error, unpinResult.error]} />
          </>
        )}
        {showBlock && (
          <>
            <Button onPress={handleEditModComment} variant="default/outline">
              Edit Mod Comment
            </Button>
            <Spacer />
          </>
        )}
        {showGroups && (
          <>
            <Header tag="h2" variant="header-sm/normal">
              Add to Groups
            </Header>
            {groups.map(group => (
              <DonationGroupCheckbox
                key={group.id}
                group={group}
                donation={donation}
                toggle={handleToggleGroup(group.id)}
                disabled={addResult.isLoading || removeResult.isLoading}
              />
            ))}
            <APIErrorList errors={[addResult.error, removeResult.error]} />
          </>
        )}
        {showBlock && (
          <>
            <Spacer />
            <Button variant="danger/outline" onPress={handleBlock} isDisabled={blockResult.isLoading}>
              Block
            </Button>
            <APIErrorList errors={blockResult.error} />
          </>
        )}
      </Stack>
    </Card>
  );
}
