import * as React from 'react';
import { useMutation } from 'react-query';
import { Anchor, Button, Card, Checkbox, Header, openModal, Spacer, Stack, Text } from '@spyrothon/sparx';

import { usePermission } from '@public/api/helpers/auth';
import APIClient from '@public/apiv2/APIClient';
import * as CurrencyUtils from '@public/util/currency';

import ModCommentModal from '@processing/modules/donations/ModCommentModal';
import { AdminRoutes, useAdminRoute } from '@processing/Routes';

import useDonationGroupsStore, { DonationGroup } from '../donation-groups/DonationGroupsStore';
import { loadDonations, useDonation } from '../donations/DonationsStore';

interface ReadingDonationRowPopoutProps {
  donationId: number;
  onClose: () => void;
}

function DonationGroupCheckbox({ group, donationId }: { group: DonationGroup; donationId: number }) {
  const { addDonationToGroup, removeDonationFromGroup } = useDonationGroupsStore();
  const isIncluded = group.donationIds.includes(donationId);
  const handleGroupChange = React.useCallback(() => {
    isIncluded ? removeDonationFromGroup(group.id, donationId) : addDonationToGroup(group.id, donationId);
  }, [addDonationToGroup, donationId, group.id, isIncluded, removeDonationFromGroup]);
  return <Checkbox label={group.name} checked={isIncluded} onChange={handleGroupChange} />;
}

export default function ReadingDonationRowPopout(props: ReadingDonationRowPopoutProps) {
  const { donationId, onClose } = props;
  const donation = useDonation(donationId);
  const { groups, removeDonationFromAllGroups } = useDonationGroupsStore();

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
      removeDonationFromAllGroups(donation.id);
    },
  });

  const handlePinChange = React.useCallback(() => {
    donation.pinned ? unpin.mutate() : pin.mutate();
  }, [donation.pinned, pin, unpin]);

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
        <Button onPress={handleEditModComment} variant="default/outline">
          Edit Mod Comment
        </Button>
        <Spacer />
        <Header tag="h2" variant="header-sm/normal">
          Add to Groups
        </Header>
        {groups.map(group => (
          <DonationGroupCheckbox key={group.id} group={group} donationId={donationId} />
        ))}
        <Spacer />
        <Button variant="danger/outline" onPress={handleBlock}>
          Block
        </Button>
      </Stack>
    </Card>
  );
}
