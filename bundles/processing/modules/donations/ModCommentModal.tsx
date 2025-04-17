import React from 'react';
import { Button, Card, Header, Stack, Text, TextArea } from '@faulty/gdq-design';

import APIErrorList from '@public/APIErrorList';
import { useEditDonationCommentMutation } from '@public/apiv2/hooks';
import { Donation } from '@public/apiv2/Models';
import * as CurrencyUtils from '@public/util/currency';

import RelativeTime from '../time/RelativeTime';

import styles from '../donation-groups/CreateEditDonationGroupModal.mod.css';

function renderDonationHeader(donation: Donation) {
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
            <RelativeTime time={donation.timereceived} />
          </span>
        </Text>
      </Stack>
    </Stack>
  );
}

interface ModCommentModalProps {
  donation: Donation;
  onClose: () => unknown;
}

export default function ModCommentModal(props: ModCommentModalProps) {
  const { donation, onClose } = props;

  const [comment, setComment] = React.useState(donation.modcomment ?? '');

  const [saveComment, saveCommentResult] = useEditDonationCommentMutation();

  const handleSave = React.useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      const { data } = await saveComment({ id: donation.id, comment });
      if (data) {
        onClose();
      }
    },
    [comment, donation, onClose, saveComment],
  );

  return (
    <Stack asChild spacing="space-lg">
      <form action="" onSubmit={handleSave} className={styles.modal}>
        <Header tag="h1">Edit Mod Comment</Header>
        <Card level={1}>{renderDonationHeader(donation)}</Card>
        <TextArea label="Mod Comment" value={comment} onChange={setComment} name="comment" />
        <Stack direction="horizontal" justify="space-between">
          <Button variant="primary" type="submit" isDisabled={saveCommentResult.isLoading}>
            Save Comment
          </Button>
        </Stack>
        <APIErrorList errors={saveCommentResult.error} />
      </form>
    </Stack>
  );
}
