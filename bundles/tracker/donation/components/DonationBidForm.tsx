import * as React from 'react';
import classNames from 'classnames';
import { useSelector } from 'react-redux';

import { useCachedCallback } from '@public/hooks/useCachedCallback';
import * as CurrencyUtils from '@public/util/currency';
import Button from '@uikit/Button';
import Checkbox from '@uikit/Checkbox';
import CurrencyInput from '@uikit/CurrencyInput';
import Header from '@uikit/Header';
import ProgressBar from '@uikit/ProgressBar';
import Text from '@uikit/Text';
import TextInput from '@uikit/TextInput';

import * as EventDetailsStore from '@tracker/event_details/EventDetailsStore';
import { StoreState } from '@tracker/Store';

import * as DonationStore from '../DonationStore';
import { Bid } from '../DonationTypes';
import validateBid from '../validateBid';

import styles from './DonationBidForm.mod.css';

type DonationBidFormProps = {
  incentiveId: number;
  step: number;
  total: number;
  className?: string;
  onSubmit: (bid: Bid) => void;
};

const DonationBidForm = (props: DonationBidFormProps) => {
  const { incentiveId, step, total: donationTotal, className, onSubmit } = props;

  const { incentive, bidChoices, donation, bids, allocatedTotal } = useSelector((state: StoreState) => ({
    incentive: EventDetailsStore.getIncentive(state, incentiveId),
    bidChoices: EventDetailsStore.getChildIncentives(state, incentiveId),
    donation: DonationStore.getDonation(state),
    bids: DonationStore.getBids(state),
    allocatedTotal: DonationStore.getAllocatedBidTotal(state),
  }));

  const remainingDonationTotal = donationTotal - allocatedTotal;
  const remainingDonationTotalString = CurrencyUtils.asCurrency(remainingDonationTotal);

  const [allocatedAmount, setAllocatedAmount] = React.useState(remainingDonationTotal);
  const [selectedChoiceId, setSelectedChoiceId] = React.useState<number | undefined>(undefined);
  const [customOptionSelected, setCustomOptionSelected] = React.useState(false);
  const [customOption, setCustomOption] = React.useState('');

  const bidValidation = React.useMemo(
    () =>
      validateBid(
        {
          incentiveId: selectedChoiceId != null ? selectedChoiceId : incentiveId,
          amount: allocatedAmount,
          customoptionname: customOption,
        },
        incentive,
        donation,
        bids,
        bidChoices.length > 0,
        selectedChoiceId != null,
        customOptionSelected,
      ),
    [
      selectedChoiceId,
      incentiveId,
      allocatedAmount,
      customOption,
      incentive,
      donation,
      bids,
      bidChoices.length,
      customOptionSelected,
    ],
  );

  const handleNewChoice = useCachedCallback(choiceId => {
    setSelectedChoiceId(choiceId);
    setCustomOptionSelected(choiceId == null);
  }, []);

  const handleSubmitBid = React.useCallback(() => {
    onSubmit({
      incentiveId: selectedChoiceId != null ? selectedChoiceId : incentiveId,
      customoptionname: customOption,
      amount: allocatedAmount,
    });
  }, [onSubmit, incentiveId, selectedChoiceId, allocatedAmount, customOption]);

  if (incentive == null) {
    return (
      <div className={classNames(styles.container, className)}>
        <Text>You have {remainingDonationTotalString} remaining.</Text>
      </div>
    );
  }

  return (
    <div className={classNames(styles.container, className)}>
      <Header size={Header.Sizes.H4}>{incentive.runname}</Header>
      <Header size={Header.Sizes.H5}>{incentive.name}</Header>
      <Text size={Text.Sizes.SIZE_14}>{incentive.description}</Text>

      {incentive.goal ? (
        <React.Fragment>
          <ProgressBar className={styles.progressBar} progress={(incentive.amount / incentive.goal) * 100} />
          <Text marginless>
            Current Raised Amount:{' '}
            <span>
              {CurrencyUtils.asCurrency(incentive.amount)} / {CurrencyUtils.asCurrency(incentive.goal)}
            </span>
          </Text>
        </React.Fragment>
      ) : null}

      <CurrencyInput
        value={allocatedAmount}
        name="incentiveBidAmount"
        label="Amount to put towards incentive"
        hint={
          <React.Fragment>
            You have <strong>{remainingDonationTotalString}</strong> remaining.
          </React.Fragment>
        }
        onChange={setAllocatedAmount}
        step={step}
        min={0}
        max={remainingDonationTotal}
      />

      {bidChoices.length > 0
        ? bidChoices.map(choice => (
            <Checkbox
              key={choice.id}
              checked={selectedChoiceId === choice.id}
              contentClassName={styles.choiceLabel}
              look={Checkbox.Looks.DENSE}
              onChange={handleNewChoice(choice.id)}>
              <Checkbox.Header>{choice.name}</Checkbox.Header>
              <span className={styles.choiceAmount}>${choice.amount}</span>
            </Checkbox>
          ))
        : null}

      {incentive.custom ? (
        <Checkbox
          label="Nominate a new option!"
          name="incentiveBidNewOption"
          checked={customOptionSelected}
          look={Checkbox.Looks.NORMAL}
          onChange={handleNewChoice(null)}>
          <TextInput
            value={customOption}
            name="incentiveBidCustomOption"
            disabled={!customOptionSelected}
            placeholder="Enter Option Here"
            onChange={setCustomOption}
            maxLength={incentive.maxlength}
          />
        </Checkbox>
      ) : null}

      {!bidValidation.valid && <Text>{bidValidation.errors.map(error => error.message)}</Text>}

      <Button
        disabled={!bidValidation.valid}
        fullwidth
        onClick={handleSubmitBid}
        data-testid="incentiveBidForm-submitBid">
        Add
      </Button>
    </div>
  );
};

export default DonationBidForm;
