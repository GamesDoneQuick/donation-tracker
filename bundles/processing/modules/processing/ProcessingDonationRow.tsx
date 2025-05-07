import React from 'react';
import { Button, openModal, openPopout, PressEvent, Stack, Text, useTooltip } from '@faulty/gdq-design';

import {
  useApproveDonationCommentMutation,
  useDenyDonationCommentMutation,
  UseDonationMutation,
  usePermission,
} from '@public/apiv2/hooks';
import { Donation } from '@public/apiv2/Models';
import Approve from '@uikit/icons/Approve';
import Comment from '@uikit/icons/Comment';
import Deny from '@uikit/icons/Deny';
import Dots from '@uikit/icons/Dots';
import SendForward from '@uikit/icons/SendForward';

import { useGroupsForDonation } from '@processing/modules/donation-groups/DonationGroupsStore';
import getEstimatedReadingTime from '@processing/modules/donations/getEstimatedReadingTIme';
import ReadingDonationRowPopout from '@processing/modules/reading/ReadingDonationRowPopout';
import ShortTime from '@processing/modules/time/ShortTime';

import DonationRow, { DonationRowGroups } from '../donations/DonationRow';
import ModCommentModal from '../donations/ModCommentModal';
import ModCommentTooltip from '../donations/ModCommentTooltip';
import MutationButton from '../processing/MutationButton';

interface ProcessingActionsProps {
  donation: Donation;
  useAction: UseDonationMutation;
  actionName: string;
  actionLabel: string;
}

function ProcessingActions(props: ProcessingActionsProps) {
  const { donation, actionName, useAction, actionLabel } = props;

  const approve = useApproveDonationCommentMutation();
  const deny = useDenyDonationCommentMutation();

  const handleEditModComment = React.useCallback(() => {
    openModal(props => <ModCommentModal donation={donation} {...props} />);
  }, [donation]);

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
    [actionLabel, donation],
  );

  const mutation = useAction();

  const loading = mutation[1].isLoading || approve[1].isLoading || deny[1].isLoading;

  return (
    <Stack direction="horizontal">
      <Button onPress={handleEditModComment} variant="link/filled" icon={Comment} />
      <MutationButton
        mutation={mutation[0]}
        actionName={actionName}
        donationId={donation.id}
        icon={SendForward}
        variant="success"
        label={actionLabel}
        data-testid="action-send"
      />
      <MutationButton
        mutation={approve[0]}
        actionName="Approved"
        donationId={donation.id}
        icon={Approve}
        label="Approve Only"
        data-testid="action-approve"
        disabled={loading}
      />
      <MutationButton
        mutation={deny[0]}
        actionName="Denied"
        donationId={donation.id}
        icon={Deny}
        label="Block"
        variant="danger"
        data-testid="action-deny"
        disabled={loading}
      />
      <Button {...moreActionsTooltipProps} onPress={handleMoreActions} variant="default">
        <Dots />
      </Button>
    </Stack>
  );
}

interface ProcessingDonationRowProps {
  donation: Donation;
  useAction: UseDonationMutation;
  actionName: string;
  actionLabel: string;
}

export default function ProcessingDonationRow(props: ProcessingDonationRowProps) {
  const { donation, useAction, actionName, actionLabel } = props;

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

    if (groups.length) {
      elements.push(<DonationRowGroups groups={groups} />);
    }

    elements.push(
      <span>
        <ShortTime time={donation.timereceived} />
      </span>,
      <span>{readingTime} to read</span>,
    );
    return elements;
  }, [donation.timereceived, groups, modComment, readingTime]);

  const canChangeDonations = usePermission('tracker.change_donation');

  const renderActions = React.useCallback(
    () =>
      canChangeDonations && (
        <ProcessingActions
          donation={donation}
          useAction={useAction}
          actionName={actionName}
          actionLabel={actionLabel}
        />
      ),
    [useAction, actionLabel, actionName, canChangeDonations, donation],
  );

  return (
    <DonationRow donation={donation} showBids getBylineElements={getBylineElements} renderActions={renderActions} />
  );
}
