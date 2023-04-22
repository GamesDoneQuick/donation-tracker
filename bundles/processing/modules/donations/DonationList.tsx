import * as React from 'react';
import { CSSTransition, TransitionGroup } from 'react-transition-group';
import { Text } from '@spyrothon/sparx';

import type { Donation } from '@public/apiv2/APITypes';
import Spinner from '@public/spinner';

import styles from './DonationList.mod.css';

interface DonationListProps {
  isError?: boolean;
  isLoading?: boolean;
  donations: Donation[];
  renderDonationRow: (donation: Donation) => React.ReactElement;
}

export default function DonationList(props: DonationListProps) {
  const { isError = false, isLoading = false, donations, renderDonationRow } = props;

  if (isLoading) {
    return (
      <div className={styles.endOfList}>
        <Spinner />
      </div>
    );
  }

  if (isError) {
    return <Text className={styles.endOfList}>Failed to load donations. Refresh the page to try again.</Text>;
  }

  return (
    <TransitionGroup>
      {donations.map(donation => (
        <CSSTransition
          key={donation.id}
          timeout={240}
          classNames={{
            enter: styles.donationEnter,
            enterActive: styles.donationEnterActive,
            exit: styles.donationExit,
            exitActive: styles.donationExitActive,
          }}>
          {renderDonationRow(donation)}
        </CSSTransition>
      ))}
    </TransitionGroup>
  );
}
