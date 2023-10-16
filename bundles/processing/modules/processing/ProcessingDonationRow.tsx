import * as React from 'react';
import { useMutation } from 'react-query';
import { Anchor, Button, openModal, Stack, Text } from '@spyrothon/sparx';

import { usePermission } from '@public/api/helpers/auth';
import APIClient from '@public/apiv2/APIClient';
import type { Donation } from '@public/apiv2/APITypes';
import TimeUtils from '@public/util/TimeUtils';
import Approve from '@uikit/icons/Approve';
import Comment from '@uikit/icons/Comment';
import Deny from '@uikit/icons/Deny';
import SendForward from '@uikit/icons/SendForward';

import { loadDonations } from '@processing/modules/donations/DonationsStore';
import getEstimatedReadingTime from '@processing/modules/donations/getEstimatedReadingTIme';

import { AdminRoutes, useAdminRoute } from '../../Routes';
import DonationRow from '../donations/DonationRow';
import ModCommentModal from '../donations/ModCommentModal';
import ModCommentTooltip from '../donations/ModCommentTooltip';
import MutationButton from '../processing/MutationButton';
import useProcessingStore from '../processing/ProcessingStore';

function useDonationMutation(mutation: (donationId: number) => Promise<Donation>, actionLabel: string) {
  const store = useProcessingStore();
  return useMutation(mutation, {
    onSuccess: (donation: Donation) => {
      loadDonations([donation]);
      store.processDonation(donation, actionLabel);
    },
  });
}

interface ProcessingActionsProps {
  donation: Donation;
  action: (donationId: string) => Promise<Donation>;
  actionName: string;
  actionLabel: string;
}

function ProcessingActions(props: ProcessingActionsProps) {
  const { donation, action, actionName, actionLabel } = props;

  const mutation = useDonationMutation((donationId: number) => action(`${donationId}`), actionName);
  const approve = useDonationMutation(
    (donationId: number) => APIClient.approveDonationComment(`${donationId}`),
    'Approved',
  );
  const deny = useDonationMutation((donationId: number) => APIClient.denyDonationComment(`${donationId}`), 'Blocked');

  const handleEditModComment = React.useCallback(() => {
    openModal(props => <ModCommentModal donationId={donation.id} {...props} />);
  }, [donation.id]);

  return (
    <Stack direction="horizontal">
      <Button onPress={handleEditModComment} variant="link/filled" icon={Comment}></Button>
      <MutationButton
        mutation={mutation}
        donationId={donation.id}
        icon={SendForward}
        variant="success"
        label={actionLabel}
      />
      <MutationButton mutation={approve} donationId={donation.id} icon={Approve} label="Approve Only" />
      <MutationButton mutation={deny} donationId={donation.id} icon={Deny} label="Block" variant="danger" />
    </Stack>
  );
}

interface ProcessingDonationRowProps {
  donation: Donation;
  action: (donationId: string) => Promise<Donation>;
  actionName: string;
  actionLabel: string;
}

export default function ProcessingDonationRow(props: ProcessingDonationRowProps) {
  const { donation, action, actionName, actionLabel } = props;
  const timestamp = TimeUtils.parseTimestamp(donation.timereceived);

  const donationLink = useAdminRoute(AdminRoutes.DONATION(donation.id));
  const donorLink = useAdminRoute(AdminRoutes.DONOR(donation.donor));
  const canEditDonors = usePermission('tracker.change_donor');

  const readingTime = getEstimatedReadingTime(donation.comment);
  const hasModComment = donation.modcomment != null && donation.modcomment.length > 0;

  const getBylineElements = React.useCallback(() => {
    const elements = [];

    if (hasModComment) {
      elements.push(
        <Text tag="span" variant="text-sm/normal">
          <ModCommentTooltip comment={donation.modcomment!} />
        </Text>,
      );
    }

    elements.push(
      <Anchor href={donationLink} newTab>
        Edit Donation
      </Anchor>,
    );
    if (canEditDonors && donation.donor != null) {
      elements.push(
        <Anchor href={donorLink} newTab>
          Edit Donor
        </Anchor>,
      );
    }

    elements.push(<span>{timestamp.toFormat('hh:mm:ss a')}</span>, <span>{readingTime} to read</span>);
    return elements;
  }, [
    canEditDonors,
    donation.donor,
    donation.modcomment,
    donationLink,
    donorLink,
    hasModComment,
    readingTime,
    timestamp,
  ]);

  const renderActions = React.useCallback(
    () => <ProcessingActions donation={donation} action={action} actionName={actionName} actionLabel={actionLabel} />,
    [action, actionLabel, actionName, donation],
  );

  return (
    <DonationRow donation={donation} showBids getBylineElements={getBylineElements} renderActions={renderActions} />
  );
}
