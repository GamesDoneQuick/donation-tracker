import React from 'react';
import { useMutation } from 'react-query';
import { Button, Card, Header, Stack, Text, TextArea } from '@faulty/gdq-design';
import { Donation } from '@gamesdonequick/donation-tracker-api-types';

import APIClient from '@public/apiv2/APIClient';
import * as CurrencyUtils from '@public/util/currency';
import TimeUtils from '@public/util/TimeUtils';

import RelativeTime from '../time/RelativeTime';
import { useDonation } from './DonationsStore';

import styles from '../donation-groups/CreateEditDonationGroupModal.mod.css';

function renderDonationHeader(donation: Donation) {
  const timestamp = TimeUtils.parseTimestamp(donation.timereceived);
  const amount = CurrencyUtils.asCurrency(donation.amount, { currency: donation.currency });

  return (
    <Stack spacing="space-sm">
      <Text variant="text-md/normal">
        <strong>{amount}</strong>
        {' from '}
        <strong>{donation.donor_name}</strong>
      </Text>
      <Stack direction="horizontal" spacing="space-sm" align="center">
        <Text variant="text-sm/normal">
          #{donation.id}
          {' · '}
          <span>
            <RelativeTime time={timestamp.toJSDate()} />
          </span>
        </Text>
      </Stack>
    </Stack>
  );
}

interface ModCommentModalProps {
  donationId: number;
  onClose: () => unknown;
}

export default function ModCommentModal(props: ModCommentModalProps) {
  const { donationId, onClose } = props;

  const donation = useDonation(donationId);
  const [comment, setComment] = React.useState(donation.modcomment ?? '');

  const saveComment = useMutation((comment: string) => APIClient.editModComment(donationId, comment));

  const handleSave = React.useCallback(
    (event: React.FormEvent) => {
      event.preventDefault();
      saveComment.mutate(comment);
      onClose();
    },
    [comment, onClose, saveComment],
  );

  return (
    <Stack asChild spacing="space-lg">
      <form action="" onSubmit={handleSave} className={styles.modal}>
        <Header tag="h1">Edit Mod Comment</Header>
        <Card level={1}>{renderDonationHeader(donation)}</Card>
        <TextArea
          label="Mod Comment"
          value={comment}
          // eslint-disable-next-line react/jsx-no-bind
          onChange={comment => setComment(comment)}
          name="comment"
        />
        <Stack direction="horizontal" justify="space-between">
          <Button variant="primary" type="submit">
            Save Comment
          </Button>
        </Stack>
      </form>
    </Stack>
  );
}
