import * as React from 'react';
import { useMutation } from 'react-query';
import { useSelector } from 'react-redux';
import { Anchor, Button, Card, Checkbox, Header, openModal, Spacer, Stack, Text } from '@spyrothon/sparx';

import { usePermission } from '@public/api/helpers/auth';
import APIClient from '@public/apiv2/APIClient';
import * as CurrencyUtils from '@public/util/currency';

import ModCommentModal from '@processing/modules/donations/ModCommentModal';
import { AdminRoutes, useAdminRoute } from '@processing/Routes';
import * as EventDetailsStore from '@tracker/event_details/EventDetailsStore';

import useDonationGroupsStore from '../donation-groups/DonationGroupsStore';
import { loadDonations, useDonation } from '../donations/DonationsStore';

interface ReadingDonationRowPopoutProps {
  donationId: number;
  onClose: () => void;
}

export default function ReadingDonationRowPopout(props: ReadingDonationRowPopoutProps) {
  const { donationId, onClose } = props;
  const donation = useDonation(donationId);
  const { groups, addDonationToGroup, removeDonationFromGroup, removeDonationFromAllGroups } = useDonationGroupsStore();
  const currency = useSelector(EventDetailsStore.getEventCurrency);

  const amount = CurrencyUtils.asCurrency(donation.amount, { currency });
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
    onClose();
    block.mutate();
  }

  function handleEditModComment() {
    onClose();
    openModal(props => <ModCommentModal donationId={donation.id} {...props} />);
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
        <Button onClick={handleEditModComment} variant="default/outline">
          Edit Mod Comment
        </Button>
        <Spacer />
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
        <Spacer />
        <Button variant="danger/outline" onClick={handleBlock}>
          Block
        </Button>
      </Stack>
    </Card>
  );
}
