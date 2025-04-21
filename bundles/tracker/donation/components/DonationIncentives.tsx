import React from 'react';
import cn from 'classnames';

import { DonationPostBid, TreeBid } from '@public/apiv2/APITypes';
import { useCachedCallback } from '@public/hooks/useCachedCallback';
import Button from '@uikit/Button';
import Clickable from '@uikit/Clickable';
import Header from '@uikit/Header';
import Text from '@uikit/Text';
import TextInput from '@uikit/TextInput';

import { DonationFormEntry } from '@tracker/donation/validateDonation';

import DonationBidForm from './DonationBidForm';
import DonationBids from './DonationBids';

import styles from './DonationIncentives.mod.css';

type DonationIncentivesProps = {
  bids: TreeBid[];
  donation: DonationFormEntry;
  addBid: (bid: DonationPostBid) => void;
  deleteBid: (bid: DonationPostBid) => void;
  className?: cn.Argument;
};

const DonationIncentives = (props: DonationIncentivesProps) => {
  const { addBid, className, bids, donation, deleteBid } = props;

  const [search, setSearch] = React.useState('');
  const [selectedIncentiveId, setSelectedIncentiveId] = React.useState<number | null>(null);
  const [showForm, setShowForm] = React.useState(false);
  const setShowFormTrue = React.useCallback(() => setShowForm(true), []);
  const searchResults = bids.filter(b => b.full_name.includes(search));
  const total = donation.bids.reduce((total, b) => total + b.amount, 0);
  const canAddBid = donation.amount != null && donation.amount > total;

  const handleSubmitBid = React.useCallback(
    (bid: DonationPostBid) => {
      setSelectedIncentiveId(null);
      addBid(bid);
      setShowForm(false);
    },
    [addBid],
  );

  const selectIncentive = useCachedCallback(resultId => setSelectedIncentiveId(resultId), []);

  return (
    <div className={cn(className)}>
      <DonationBids className={styles.bids} bids={bids} donation={donation} deleteBid={deleteBid} />

      {showForm ? (
        <div className={styles.incentives}>
          <div className={styles.left}>
            <TextInput value={search} onChange={setSearch} name="filter" placeholder="Filter Incentives" marginless />
            <div className={styles.results}>
              {searchResults.map(result => (
                <Clickable
                  className={cn(styles.result, {
                    [styles.resultSelected]: selectedIncentiveId === result.id,
                  })}
                  key={result.id}
                  onClick={selectIncentive(result.id)}
                  data-testid={`incentiveform-incentive-${result.id}`}>
                  {result.full_name.includes(' -- ') && (
                    <Header size={Header.Sizes.H5} marginless oneline>
                      {result.full_name.split(' -- ').slice(0, -1).join(' -- ')}
                    </Header>
                  )}
                  <Text size={Text.Sizes.SIZE_14} marginless oneline>
                    {result.name}
                    {result.chain_steps && ` (${result.chain_steps.length + 1} steps)`}
                  </Text>
                </Clickable>
              ))}
            </div>
          </div>

          {selectedIncentiveId != null ? (
            <DonationBidForm
              key={selectedIncentiveId} // reset the form if the incentive changes
              bids={bids}
              className={styles.right}
              incentiveId={selectedIncentiveId}
              donation={donation}
              onSubmit={handleSubmitBid}
            />
          ) : (
            <div className={styles.right} />
          )}
        </div>
      ) : (
        <Button
          disabled={!canAddBid}
          look={Button.Looks.OUTLINED}
          fullwidth
          onClick={setShowFormTrue}
          data-testid="addincentives-button">
          {bids.length > 0 ? 'Add Another Incentive' : 'Add Incentives'}
        </Button>
      )}
    </div>
  );
};

export default DonationIncentives;
