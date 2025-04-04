import React from 'react';
import { useMutation } from 'react-query';
import { Button, openModal, openPopout, PressEvent, Stack, Text, useTooltip } from '@faulty/gdq-design';

import APIClient from '@public/apiv2/APIClient';
import type { APIDonation as Donation } from '@public/apiv2/APITypes';
import { usePermission } from '@public/apiv2/helpers/auth';
import TimeUtils from '@public/util/TimeUtils';
import Approve from '@uikit/icons/Approve';
import Comment from '@uikit/icons/Comment';
import Deny from '@uikit/icons/Deny';
import Dots from '@uikit/icons/Dots';
import SendForward from '@uikit/icons/SendForward';

import { useGroupsForDonation } from '@processing/modules/donation-groups/DonationGroupsStore';
import { loadDonations } from '@processing/modules/donations/DonationsStore';
import getEstimatedReadingTime from '@processing/modules/donations/getEstimatedReadingTIme';
import ReadingDonationRowPopout from '@processing/modules/reading/ReadingDonationRowPopout';

import DonationRow, { DonationRowGroups } from '../donations/DonationRow';
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
  action: (donationId: number) => Promise<Donation>;
  actionName: string;
  actionLabel: string;
}

function ProcessingActions(props: ProcessingActionsProps) {
  const { donation, action, actionName, actionLabel } = props;

  const mutation = useDonationMutation((donationId: number) => action(donationId), actionName);
  const approve = useDonationMutation((donationId: number) => APIClient.approveDonationComment(donationId), 'Approved');
  const deny = useDonationMutation((donationId: number) => APIClient.denyDonationComment(donationId), 'Blocked');

  const handleEditModComment = React.useCallback(() => {
    openModal(props => <ModCommentModal donationId={donation.id} {...props} />);
  }, [donation.id]);

  const [moreActionsTooltipProps] = useTooltip<HTMLButtonElement>('More Actions');
  const handleMoreActions = React.useCallback(
    (event: PressEvent) => {
      openPopout(
        props => (
          <ReadingDonationRowPopout
            {...props}
            showBlock={false}
            showPin={actionLabel === 'Send to Reader'}
            showGroups={actionLabel === 'Send to Reader'}
            donationId={donation.id}
          />
        ),
        event.target,
      );
    },
    [actionLabel, donation.id],
  );

  return (
    <Stack direction="horizontal">
      <Button onPress={handleEditModComment} variant="link/filled" icon={Comment} />
      <MutationButton
        mutation={mutation}
        donationId={donation.id}
        icon={SendForward}
        variant="success"
        label={actionLabel}
        data-test-id="send"
      />
      <MutationButton
        mutation={approve}
        donationId={donation.id}
        icon={Approve}
        label="Approve Only"
        data-test-id="approve"
      />
      <MutationButton
        mutation={deny}
        donationId={donation.id}
        icon={Deny}
        label="Block"
        variant="danger"
        data-test-id="deny"
      />
      <Button {...moreActionsTooltipProps} onPress={handleMoreActions} variant="default">
        <Dots />
      </Button>
    </Stack>
  );
}

interface ProcessingDonationRowProps {
  donation: Donation;
  action: (donationId: number) => Promise<Donation>;
  actionName: string;
  actionLabel: string;
}

export default function ProcessingDonationRow(props: ProcessingDonationRowProps) {
  const { donation, action, actionName, actionLabel } = props;
  const timestamp = TimeUtils.parseTimestamp(donation.timereceived);

  const readingTime = getEstimatedReadingTime(donation.comment);
  const modComment = donation?.modcomment || '';

  const groups = useGroupsForDonation(donation);

  const getBylineElements = React.useCallback(() => {
    const elements = [];

    if (modComment) {
      elements.push(
        <Text tag="span" variant="text-sm/normal">
          <ModCommentTooltip comment={modComment} />
        </Text>,
      );
    }

    elements.push(<DonationRowGroups groups={groups} />);

    elements.push(<span>{timestamp.toFormat('hh:mm:ss a')}</span>, <span>{readingTime} to read</span>);
    return elements;
  }, [groups, modComment, readingTime, timestamp]);

  const canChangeDonations = usePermission('tracker.change_donation');

  const renderActions = React.useCallback(
    () =>
      canChangeDonations && (
        <ProcessingActions donation={donation} action={action} actionName={actionName} actionLabel={actionLabel} />
      ),
    [action, actionLabel, actionName, canChangeDonations, donation],
  );

  return (
    <DonationRow donation={donation} showBids getBylineElements={getBylineElements} renderActions={renderActions} />
  );
}
