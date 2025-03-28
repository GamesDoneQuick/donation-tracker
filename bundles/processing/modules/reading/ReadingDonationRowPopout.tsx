import React from 'react';
import { useMutation } from 'react-query';
import { Anchor, Button, Card, Checkbox, Header, openModal, Spacer, Stack, Text } from '@faulty/gdq-design';

import APIClient from '@public/apiv2/APIClient';
import { APIDonation as Donation } from '@public/apiv2/APITypes';
import { usePermission } from '@public/apiv2/helpers/auth';
import { addDonationToGroup, removeDonationFromGroup } from '@public/apiv2/routes/donations';
import { useCachedCallback } from '@public/hooks/useCachedCallback';
import * as CurrencyUtils from '@public/util/currency';

import ModCommentModal from '@processing/modules/donations/ModCommentModal';
import { AdminRoutes, useAdminRoute } from '@processing/Routes';

import useDonationGroupsStore, { DonationGroup } from '../donation-groups/DonationGroupsStore';
import { loadDonations, useDonation } from '../donations/DonationsStore';

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
  const donation = useDonation(donationId);
  const { groups } = useDonationGroupsStore();

  const amount = CurrencyUtils.asCurrency(donation.amount, { currency: donation.currency });
  const donationLink = useAdminRoute(AdminRoutes.DONATION(donation.id));
  const donorLink = useAdminRoute(AdminRoutes.DONOR(donation.donor));
  const canEditDonors = usePermission('tracker.change_donor');

  const pin = useMutation(() => APIClient.pinDonation(donation.id), {
    onSuccess: donation => loadDonations([donation]),
  });
  const unpin = useMutation(() => APIClient.unpinDonation(donation.id), {
    onSuccess: donation => loadDonations([donation]),
  });
  const block = useMutation(() => APIClient.denyDonationComment(donation.id), {
    onSuccess: donation => {
      loadDonations([donation]);
    },
  });
  const toggleGroup = useMutation(
    (group: string) => {
      const isIncluded = donation.groups?.includes(group) || false;
      return isIncluded ? removeDonationFromGroup(donation.id, group) : addDonationToGroup(donation.id, group);
    },
    {
      onSuccess: groups => {
        loadDonations([{ ...donation, groups }]);
      },
    },
  );

  const handlePinChange = React.useCallback(() => {
    donation.pinned ? unpin.mutate() : pin.mutate();
  }, [donation.pinned, pin, unpin]);

  const handleToggleGroup = useCachedCallback(
    (group: string) => {
      toggleGroup.mutate(group);
    },
    [toggleGroup],
  );

  const handleBlock = React.useCallback(() => {
    onClose();
    block.mutate();
  }, [block, onClose]);

  const handleEditModComment = React.useCallback(() => {
    onClose();
    openModal(props => <ModCommentModal donationId={donation.id} {...props} />);
  }, [donation.id, onClose]);

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
          <Checkbox
            label="Pin for Everyone"
            isDisabled={pin.isLoading || unpin.isLoading}
            checked={donation.pinned}
            onChange={handlePinChange}
          />
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
                disabled={toggleGroup.isLoading}
              />
            ))}
          </>
        )}
        {showBlock && (
          <>
            <Spacer />
            <Button variant="danger/outline" onPress={handleBlock}>
              Block
            </Button>
          </>
        )}
      </Stack>
    </Card>
  );
}
