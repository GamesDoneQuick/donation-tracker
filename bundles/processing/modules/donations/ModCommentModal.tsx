import * as React from 'react';
import { useMutation } from 'react-query';
import { useSelector } from 'react-redux';
import { Button, Card, FormControl, Header, Stack, Text, TextArea } from '@spyrothon/sparx';

import APIClient from '@public/apiv2/APIClient';
import { Donation } from '@public/apiv2/APITypes';
import * as CurrencyUtils from '@public/util/currency';
import TimeUtils from '@public/util/TimeUtils';

import * as EventDetailsStore from '@tracker/event_details/EventDetailsStore';

import RelativeTime from '../time/RelativeTime';
import { useDonation } from './DonationsStore';

import styles from '../donation-groups/CreateEditDonationGroupModal.mod.css';

function renderDonationHeader(donation: Donation, currency: string) {
  const timestamp = TimeUtils.parseTimestamp(donation.timereceived);
  const amount = CurrencyUtils.asCurrency(donation.amount, { currency });

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

  const currency = useSelector(EventDetailsStore.getEventCurrency);
  const donation = useDonation(donationId);
  const [comment, setComment] = React.useState(donation.modcomment ?? '');

  const saveComment = useMutation((comment: string) => APIClient.editModComment(`${donationId}`, comment));

  function handleSave(event: React.FormEvent) {
    event.preventDefault();
    saveComment.mutate(comment);
    onClose();
  }

  return (
    <Card floating className={styles.modal}>
      <Stack as="form" spacing="space-lg" action="" onSubmit={handleSave}>
        <Header tag="h1">Edit Mod Comment</Header>
        <Card>{renderDonationHeader(donation, currency)}</Card>
        <FormControl label="Mod Comment">
          <TextArea
            value={comment}
            // eslint-disable-next-line react/jsx-no-bind
            onChange={event => setComment(event.target.value)}
            name="comment"
          />
        </FormControl>
        <Stack direction="horizontal" justify="space-between">
          <Button variant="primary" type="submit">
            Save Comment
          </Button>
        </Stack>
      </Stack>
    </Card>
  );
}
