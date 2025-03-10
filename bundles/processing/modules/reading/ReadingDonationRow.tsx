import React from 'react';
import { useMutation } from 'react-query';
import { Button, openPopout, PressEvent, Stack, Text, useTooltip } from '@faulty/gdq-design';

import APIClient from '@public/apiv2/APIClient';
import { APIDonation as Donation } from '@public/apiv2/APITypes';
import TimeUtils from '@public/util/TimeUtils';
import Approve from '@uikit/icons/Approve';
import Deny from '@uikit/icons/Deny';
import Dots from '@uikit/icons/Dots';

import {
  DonationGroup,
  forgetOrderingForDonation,
  moveDonationWithinGroup,
  useGroupsForDonation,
} from '../donation-groups/DonationGroupsStore';
import DonationRow, { DonationRowGroups } from '../donations/DonationRow';
import { loadDonations } from '../donations/DonationsStore';
import getEstimatedReadingTime from '../donations/getEstimatedReadingTIme';
import ModCommentTooltip from '../donations/ModCommentTooltip';
import MutationButton from '../processing/MutationButton';
import RelativeTime from '../time/RelativeTime';
import ReadingDonationRowPopout from './ReadingDonationRowPopout';

interface ReadingActionsProps {
  donation: Donation;
}

function ReadingActions(props: ReadingActionsProps) {
  const { donation } = props;

  const read = useMutation((donationId: number) => APIClient.readDonation(donationId), {
    onSuccess: (donation: Donation) => {
      loadDonations([donation]);
      forgetOrderingForDonation(donation.id);
    },
  });
  const ignore = useMutation((donationId: number) => APIClient.ignoreDonation(donationId), {
    onSuccess: (donation: Donation) => {
      loadDonations([donation]);
      forgetOrderingForDonation(donation.id);
    },
  });

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
    [donation.id],
  );

  return (
    <Stack direction="horizontal">
      <MutationButton mutation={read} donationId={donation.id} icon={Approve} label="Mark as Read" variant="success" />
      <MutationButton mutation={ignore} donationId={donation.id} icon={Deny} label="Mark as Ignored" variant="danger" />
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
  const { donation, draggable, currentGroupId } = props;
  const timestamp = TimeUtils.parseTimestamp(donation.timereceived);

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

    elements.push(<DonationRowGroups groups={groups} />);

    elements.push(
      <span>
        <RelativeTime time={timestamp.toJSDate()} />
      </span>,
      `${readingTime} to read`,
    );

    return elements;
  }, [donation.modcomment, groups, hasModComment, readingTime, timestamp]);

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
    />
  );
}
