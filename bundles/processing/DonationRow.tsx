import * as React from 'react';
import classNames from 'classnames';
import Highlighter from 'react-highlight-words';
import { useMutation } from 'react-query';
import { Anchor, Stack, Text } from '@spyrothon/sparx';

import { usePermission } from '@public/api/helpers/auth';
import APIClient from '@public/apiv2/APIClient';
import type { Donation, DonationBid } from '@public/apiv2/APITypes';
import * as CurrencyUtils from '@public/util/currency';
import TimeUtils from '@public/util/TimeUtils';
import Approve from '@uikit/icons/Approve';
import Deny from '@uikit/icons/Deny';
import SendForward from '@uikit/icons/SendForward';

import { loadDonations } from './DonationsStore';
import getEstimatedReadingTime from './getEstimatedReadingTIme';
import MutationButton from './MutationButton';
import useProcessingStore from './ProcessingStore';
import { AdminRoutes, useAdminRoute } from './Routes';
import { useSearchKeywords } from './SearchKeywordsStore';

import styles from './DonationRow.mod.css';

function useDonationMutation(mutation: (donationId: number) => Promise<Donation>, actionLabel: string) {
  const store = useProcessingStore();
  return useMutation(mutation, {
    onSuccess: (donation: Donation) => {
      loadDonations([donation]);
      store.processDonation(donation, actionLabel);
    },
  });
}

interface BidsRowProps {
  bids: DonationBid[];
}

function BidsRow(props: BidsRowProps) {
  const { bids } = props;
  if (bids.length === 0) return null;

  const bidNames = bids.map(bid => `${bid.bid_name} (${CurrencyUtils.asCurrency(bid.amount)})`);

  return (
    <Text variant="text-sm/normal" className={styles.bids}>
      Attached Bids: {bidNames.join(' • ')}
    </Text>
  );
}

interface DonationRowProps {
  donation: Donation;
  action: (donationId: string) => Promise<Donation>;
  actionName: string;
  actionLabel: string;
}

export default function DonationRow(props: DonationRowProps) {
  const { donation, action, actionName, actionLabel } = props;
  const timestamp = TimeUtils.parseTimestamp(donation.timereceived);

  const donationLink = useAdminRoute(AdminRoutes.DONATION(donation.id));
  const donorLink = useAdminRoute(AdminRoutes.DONOR(donation.donor));
  const canEditDonors = usePermission('tracker.change_donor');

  const keywords = useSearchKeywords();
  const mutation = useDonationMutation((donationId: number) => action(`${donationId}`), actionName);
  const approve = useDonationMutation(
    (donationId: number) => APIClient.approveDonationComment(`${donationId}`),
    'Approved',
  );
  const deny = useDonationMutation((donationId: number) => APIClient.denyDonationComment(`${donationId}`), 'Blocked');

  const readingTime = getEstimatedReadingTime(donation.comment);
  const amount = CurrencyUtils.asCurrency(donation.amount);
  const hasComment = donation.comment != null && donation.comment.length > 0;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Stack direction="horizontal" justify="space-between" align="center" className={styles.headerTop}>
          <div>
            <Text variant="header-sm/normal">
              <strong>{amount}</strong>
              <Text tag="span" variant="text-md/secondary">
                {' from '}
              </Text>
              <strong>
                <Highlighter
                  highlightClassName={styles.highlighted}
                  searchWords={keywords}
                  textToHighlight={donation.donor_name || ''}
                />
              </strong>
            </Text>
            <Text variant="text-xs/secondary">
              <Anchor href={donationLink} newTab>
                Edit Donation
              </Anchor>
              {canEditDonors && donation.donor != null ? (
                <>
                  {' · '}
                  <Anchor href={donorLink} newTab>
                    Edit Donor
                  </Anchor>
                </>
              ) : null}
              {' · '}
              <span>{timestamp.toFormat('hh:mm:ss a')}</span>
              {' · '}
              <span>{readingTime} to read</span>
            </Text>
          </div>
          <Stack direction="horizontal">
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
        </Stack>
        <BidsRow bids={donation.bids} />
      </div>
      <Text
        variant={hasComment ? 'text-md/normal' : 'text-md/secondary'}
        className={classNames(styles.comment, { [styles.noCommentHint]: !hasComment })}>
        {hasComment ? (
          <Highlighter
            highlightClassName={styles.highlighted}
            searchWords={keywords}
            textToHighlight={donation.comment || ''}
          />
        ) : (
          'No comment was provided'
        )}
      </Text>
    </div>
  );
}
