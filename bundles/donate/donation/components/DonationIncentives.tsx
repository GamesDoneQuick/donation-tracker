import React from 'react';
import { useSelector } from 'react-redux';
import _ from 'lodash';
import classNames from 'classnames';

import Button from '../../../uikit/Button';
import Checkbox from '../../../uikit/Checkbox';
import Clickable from '../../../uikit/Clickable';
import Header from '../../../uikit/Header';
import ProgressBar from '../../../uikit/ProgressBar';
import Text from '../../../uikit/Text';
import TextInput from '../../../uikit/TextInput';
import useDispatch from '../../hooks/useDispatch';
import * as EventDetailsStore from '../../event_details/EventDetailsStore';
import searchIncentives from '../../event_details/searchIncentives';
import * as DonationActions from '../DonationActions';
import * as DonationStore from '../../donation/DonationStore';
import DonationBidForm from './DonationBidForm';
import DonationBids from './DonationBids';

import styles from './DonationIncentives.mod.css';

type DonationIncentivesProps = {
  step: number;
  total: number;
  className?: string;
};

const DonationIncentives = (props: DonationIncentivesProps) => {
  const { step, total, className } = props;

  const dispatch = useDispatch();

  const [search, setSearch] = React.useState('');
  const [selectedIncentiveId, setSelectedIncentiveId] = React.useState<number | undefined>(undefined);
  const [showForm, setShowForm] = React.useState(false);
  const allocatedBidTotal = useSelector(DonationStore.getAllocatedBidTotal);
  const incentives = useSelector(EventDetailsStore.getTopLevelIncentives);
  const searchResults = searchIncentives(incentives, search);
  const canAddBid = total - allocatedBidTotal > 0;

  const handleSubmitBid = React.useCallback(
    bid => {
      setSelectedIncentiveId(undefined);
      dispatch(DonationActions.createBid(bid));
      setShowForm(false);
    },
    [dispatch],
  );

  return (
    <div className={className}>
      <DonationBids className={styles.bids} />

      {showForm ? (
        <div className={styles.incentives}>
          <div className={styles.left}>
            <TextInput value={search} onChange={setSearch} name="filter" placeholder="Filter Incentives" marginless />
            <div className={styles.results}>
              {searchResults.map(result => (
                <Clickable
                  className={classNames(styles.result, {
                    [styles.resultSelected]: selectedIncentiveId === result.id,
                  })}
                  key={result.id}
                  onClick={() => setSelectedIncentiveId(result.id)}>
                  <Header size={Header.Sizes.H5} marginless oneline>
                    {result.runname}
                  </Header>
                  <Text size={Text.Sizes.SIZE_14} marginless oneline>
                    {result.name}
                  </Text>
                </Clickable>
              ))}
            </div>
          </div>

          {selectedIncentiveId != null ? (
            <DonationBidForm
              className={styles.right}
              incentiveId={selectedIncentiveId}
              step={step}
              total={total}
              onSubmit={handleSubmitBid}
            />
          ) : (
            <div className={styles.right} />
          )}
        </div>
      ) : (
        <Button disabled={!canAddBid} look={Button.Looks.OUTLINED} fullwidth onClick={() => setShowForm(true)}>
          Add Incentives
        </Button>
      )}
    </div>
  );
};

export default DonationIncentives;
