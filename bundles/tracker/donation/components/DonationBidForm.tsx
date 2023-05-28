import React from 'react';
import classNames from 'classnames';
import { shallowEqual, useSelector } from 'react-redux';

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

  const { currency, incentive, bidChoices, donation, bids, allocatedTotal } = useSelector(
    (state: StoreState) => ({
      currency: EventDetailsStore.getEventCurrency(state),
      incentive: EventDetailsStore.getIncentive(state, incentiveId),
      bidChoices: EventDetailsStore.getChildIncentives(state, incentiveId),
      donation: DonationStore.getDonation(state),
      bids: DonationStore.getBids(state),
      allocatedTotal: DonationStore.getAllocatedBidTotal(state),
    }),
    shallowEqual,
  );

  const remainingDonationTotal = donationTotal - allocatedTotal;
  const remainingDonationTotalString = CurrencyUtils.asCurrency(remainingDonationTotal, { currency });

  const [allocatedAmount, setAllocatedAmount] = React.useState(remainingDonationTotal);
  const [selectedChoiceId, setSelectedChoiceId] = React.useState<number | undefined>(undefined);
  const [customOptionSelected, setCustomOptionSelected] = React.useState(false);
  const [customOption, setCustomOption] = React.useState('');

  React.useEffect(() => {
    if (allocatedAmount > remainingDonationTotal) {
      setAllocatedAmount(remainingDonationTotal);
    }
  }, [allocatedAmount, remainingDonationTotal]);

  const bidValidation = React.useMemo(
    () =>
      validateBid(
        currency,
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
      currency,
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

  const fullGoal = (incentive.chain_remaining || 0) + (incentive.goal || 0);

  return (
    <div className={classNames(styles.container, className)}>
      <Header size={Header.Sizes.H4}>{incentive.runname}</Header>
      <Header size={Header.Sizes.H5}>{incentive.name}</Header>
      <Text size={Text.Sizes.SIZE_14}>{incentive.description}</Text>
      {incentive.accepted_number && incentive.accepted_number > 1 && (
        <Text size={Text.Sizes.SIZE_14}>Top {incentive.accepted_number} options will be used!</Text>
      )}

      {fullGoal && incentive.goal ? (
        <React.Fragment>
          {incentive.chain && (
            <>
              {CurrencyUtils.asCurrency(Math.min(incentive.amount, incentive.goal), { currency })} /{' '}
              {CurrencyUtils.asCurrency(incentive.goal, { currency })}
            </>
          )}
          <ProgressBar className={styles.progressBar} progress={(incentive.amount / incentive.goal) * 100} />
          {incentive.chain_steps?.map(step => (
            <React.Fragment key={step.id}>
              <Text size={Text.Sizes.SIZE_12}>{step.name}</Text>
              {CurrencyUtils.asCurrency(Math.min(step.amount, step.goal), { currency })} /{' '}
              {CurrencyUtils.asCurrency(step.goal, { currency })}
              <ProgressBar className={styles.progressBar} progress={(step.amount / step.goal) * 100} />
            </React.Fragment>
          ))}

          <Text marginless>
            Current Raised Amount:{' '}
            <span>
              {CurrencyUtils.asCurrency(incentive.amount, { currency })} /{' '}
              {CurrencyUtils.asCurrency(fullGoal, { currency })}
            </span>
          </Text>
        </React.Fragment>
      ) : null}

      <CurrencyInput
        value={Math.min(allocatedAmount, remainingDonationTotal)}
        name="incentiveBidAmount"
        label="Amount to put towards incentive"
        currency={currency}
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

      {bidChoices.length > 0 && !incentive.chain
        ? bidChoices.map(choice => (
            <Checkbox
              key={choice.id}
              checked={selectedChoiceId === choice.id}
              contentClassName={styles.choiceLabel}
              look={Checkbox.Looks.DENSE}
              onChange={handleNewChoice(choice.id)}>
              <Checkbox.Header>{choice.name}</Checkbox.Header>
              <span className={styles.choiceAmount}>{CurrencyUtils.asCurrency(choice.amount, { currency })}</span>
            </Checkbox>
          ))
        : null}

      {incentive.custom ? (
        <>
          <Checkbox
            label="Nominate a new option!"
            name="incentiveBidNewOption"
            checked={customOptionSelected}
            look={Checkbox.Looks.DENSE}
            onChange={handleNewChoice(null)}
          />
          {customOptionSelected ? (
            <TextInput
              value={customOption}
              name="incentiveBidCustomOption"
              placeholder="Enter Option Here"
              onChange={setCustomOption}
              maxLength={incentive.maxlength}
            />
          ) : null}
        </>
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
