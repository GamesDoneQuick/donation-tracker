import React from 'react';
import { Button, openPopout, PressEvent, Stack, Text, useTooltip } from '@faulty/gdq-design';

import { useEventFromRoute, useIgnoreDonationMutation, useReadDonationMutation } from '@public/apiv2/hooks';
import { Donation } from '@public/apiv2/Models';
import Approve from '@uikit/icons/Approve';
import Deny from '@uikit/icons/Deny';
import Dots from '@uikit/icons/Dots';

import { DonationGroup, moveDonationWithinGroup, useGroupsForDonation } from '../donation-groups/DonationGroupsStore';
import DonationRow, { DonationRowGroups } from '../donations/DonationRow';
import getEstimatedReadingTime from '../donations/getEstimatedReadingTIme';
import ModCommentTooltip from '../donations/ModCommentTooltip';
import MutationButton from '../processing/MutationButton';
import RelativeTime from '../time/RelativeTime';
import ReadingDonationRowPopout from './ReadingDonationRowPopout';

interface ReadingActionsProps {
  donation: Donation;
}

function ReadingActions(props: ReadingActionsProps) {
  const { data: event } = useEventFromRoute();
  const { donation } = props;

  const [read, readResult] = useReadDonationMutation();
  const [ignore, ignoreResult] = useIgnoreDonationMutation();

  const [moreActionsTooltipProps] = useTooltip<HTMLButtonElement>('More Actions');
  const handleMoreActions = React.useCallback(
    (event: PressEvent) => {
      openPopout(
        props => <ReadingDonationRowPopout {...props} showGroups showPin showBlock donationId={donation.id} />,
        event.target,
        {
          noStyle: true,
        },
      );
    },
    [donation],
  );

  const disabled = readResult.isLoading || ignoreResult.isLoading;

  return (
    <Stack direction="horizontal">
      <MutationButton
        mutation={read}
        donationId={donation.id}
        icon={Approve}
        label="Mark as Read"
        variant="success"
        disabled={disabled}
        data-testid="action-read"
      />
      {event?.screening_mode !== 'host_only' && (
        <MutationButton
          mutation={ignore}
          donationId={donation.id}
          icon={Deny}
          label="Mark as Ignored"
          variant="danger"
          disabled={disabled}
          data-testid="action-ignore"
        />
      )}
      <Button {...moreActionsTooltipProps} onPress={handleMoreActions} variant="default">
        <Dots />
      </Button>
    </Stack>
  );
}

interface DonationRowProps {
  donation: Donation;
  draggable: boolean;
  currentGroupId: DonationGroup['id'];
}

export default function ReadingDonationRow(props: DonationRowProps) {
  const { data: event } = useEventFromRoute();
  const { donation, draggable, currentGroupId } = props;

  const readingTime = getEstimatedReadingTime(donation.comment);
  const hasModComment = donation.modcomment != null && donation.modcomment.length > 0;

  const groups = useGroupsForDonation(donation);

  const getBylineElements = React.useCallback(() => {
    const elements = [];
    if (hasModComment) {
      elements.push(
        <Text tag="span" variant="text-sm/normal">
          <ModCommentTooltip comment={donation.modcomment ?? ''} />
        </Text>,
      );
    }

    if (groups.length) {
      elements.push(<DonationRowGroups groups={groups} />);
    }

    elements.push(
      <span>
        <RelativeTime time={donation.timereceived} />
      </span>,
      `${readingTime} to read`,
    );

    return elements;
  }, [donation, groups, hasModComment, readingTime]);

  const renderActions = React.useCallback(() => <ReadingActions donation={donation} />, [donation]);

  const onDrop = React.useCallback(
    (item: Donation) => {
      moveDonationWithinGroup(currentGroupId, item.id, donation.id);
    },
    [currentGroupId, donation.id],
  );

  const canDrop = React.useCallback((item: Donation) => item.id !== donation.id, [donation.id]);

  return (
    <DonationRow
      donation={donation}
      draggable={draggable}
      getBylineElements={getBylineElements}
      renderActions={renderActions}
      onDrop={onDrop}
      canDrop={canDrop}
      showBids={event?.screening_mode === 'host_only'}
    />
  );
}
