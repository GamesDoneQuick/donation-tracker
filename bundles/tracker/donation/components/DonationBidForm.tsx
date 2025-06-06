import React from 'react';
import cn from 'classnames';

import { compareBidChild, DonationPostBid, TreeBid } from '@public/apiv2/APITypes';
import { useEventFromRoute } from '@public/apiv2/hooks';
import { useCachedCallback } from '@public/hooks/useCachedCallback';
import { useEventCurrency } from '@public/util/currency';
import Button from '@uikit/Button';
import Checkbox from '@uikit/Checkbox';
import CurrencyInput from '@uikit/CurrencyInput';
import ErrorAlert from '@uikit/ErrorAlert';
import Header from '@uikit/Header';
import ProgressBar from '@uikit/ProgressBar';
import Text from '@uikit/Text';
import TextInput from '@uikit/TextInput';

import { DonationFormEntry } from '@tracker/donation/validateDonation';

import validateBid from '../validateBid';

import styles from './DonationBidForm.mod.css';

type DonationBidFormProps = {
  bids: TreeBid[];
  incentiveId: number;
  donation: DonationFormEntry;
  className?: cn.Argument;
  onSubmit: (bid: DonationPostBid) => void;
};

const DonationBidForm = (props: DonationBidFormProps) => {
  const { bids, incentiveId, className, onSubmit, donation } = props;
  const { data } = useEventFromRoute();
  const event = data!;

  const eventCurrency = useEventCurrency();

  const allocatedTotal = donation.bids.reduce((total, bid) => total + bid.amount, 0);
  const remainingDonationTotal = donation.amount != null ? donation.amount - allocatedTotal : 0;
  const remainingDonationTotalString = eventCurrency(remainingDonationTotal);

  const [allocatedAmount, setAllocatedAmount] = React.useState(remainingDonationTotal);
  const [selectedChoiceId, setSelectedChoiceId] = React.useState<number | null>(null);
  const [customOptionSelected, setCustomOptionSelected] = React.useState(false);
  const [customOption, setCustomOption] = React.useState('');

  const incentive = bids.find(b => b.id === incentiveId)!;
  const option = incentive.options?.find(o => o.id === selectedChoiceId) ?? null;

  React.useEffect(() => {
    if (allocatedAmount > remainingDonationTotal) {
      setAllocatedAmount(remainingDonationTotal);
    }
  }, [allocatedAmount, remainingDonationTotal]);

  const currentBid = React.useMemo((): DonationPostBid | null => {
    return incentive.options == null || customOptionSelected || selectedChoiceId != null
      ? {
          ...(customOptionSelected
            ? { parent: incentiveId, name: customOption }
            : { id: incentive.options ? selectedChoiceId! : incentiveId }),
          amount: allocatedAmount,
        }
      : null;
  }, [allocatedAmount, customOption, customOptionSelected, incentive.options, incentiveId, selectedChoiceId]);

  const bidValidation = React.useMemo(
    () => (currentBid ? validateBid(event.paypalcurrency, currentBid, incentive, donation, option) : null),
    [event.paypalcurrency, currentBid, incentive, donation, option],
  );

  const handleNewChoice = useCachedCallback(choiceId => {
    setSelectedChoiceId(choiceId);
    setCustomOptionSelected(choiceId == null);
  }, []);

  const handleSubmitBid = React.useCallback(() => {
    if (currentBid) {
      onSubmit(currentBid);
    }
  }, [onSubmit, currentBid]);

  const fullGoal = incentive?.goal != null ? incentive.goal + (incentive.chain_remaining ?? 0) : 0;
  const header = incentive.full_name.includes(' -- ')
    ? incentive.full_name.split(' -- ').slice(0, -1).join(' -- ')
    : '';

  return (
    <div className={cn(styles.container, className)}>
      {header && <Header size={Header.Sizes.H4}>{header}</Header>}
      <Header size={Header.Sizes.H5}>{incentive.name}</Header>
      <Text size={Text.Sizes.SIZE_14}>{incentive.description}</Text>
      {incentive.accepted_number && incentive.accepted_number > 1 && (
        <Text size={Text.Sizes.SIZE_14}>Top {incentive.accepted_number} options will be used!</Text>
      )}

      {incentive.goal &&
        (incentive.repeat ? (
          <>
            <Text>
              {`Repeats every ${eventCurrency(incentive.repeat)}! Only ${eventCurrency(incentive.repeat - (incentive.total % incentive.repeat))} to reach the next goal!`}
              <ProgressBar progress={((incentive.total % incentive.repeat) / incentive.repeat) * 100} />
              Total Raised: <span>{eventCurrency(incentive.total)}</span>
            </Text>
          </>
        ) : (
          <>
            {incentive.chain &&
              `${eventCurrency(Math.min(incentive.total, incentive.goal))} / ${eventCurrency(incentive.goal)}`}
            <ProgressBar className={styles.progressBar} progress={(incentive.total / incentive.goal) * 100} />
            {incentive.chain_steps?.map(step => (
              <React.Fragment key={step.id}>
                <Text size={Text.Sizes.SIZE_12}>{step.name}</Text>
                {`${eventCurrency(Math.min(step.total, step.goal))} / ${eventCurrency(step.goal)}`}
                <ProgressBar className={styles.progressBar} progress={(step.total / step.goal) * 100} />
              </React.Fragment>
            ))}
            <Text marginless>
              Total Raised: <span>{`${eventCurrency(incentive.total)} / ${eventCurrency(fullGoal)}`}</span>
            </Text>
          </>
        ))}

      <CurrencyInput
        value={Math.min(allocatedAmount, remainingDonationTotal)}
        name="incentiveBidAmount"
        label="Amount to put towards incentive"
        currency={event.paypalcurrency}
        hint={
          <React.Fragment>
            You have <strong>{remainingDonationTotalString}</strong> remaining.
          </React.Fragment>
        }
        onChange={setAllocatedAmount}
        min={0}
        max={remainingDonationTotal}
      />

      {incentive.options?.toSorted(compareBidChild).map(option => (
        <Checkbox
          key={option.id}
          checked={selectedChoiceId === option.id}
          contentClassName={styles.choiceLabel}
          look={Checkbox.Looks.DENSE}
          onChange={handleNewChoice(option.id)}>
          <Checkbox.Header>{option.name}</Checkbox.Header>
          <span className={styles.choiceAmount}>{eventCurrency(option.total)}</span>
        </Checkbox>
      ))}

      {incentive.allowuseroptions && (
        <>
          <Checkbox
            label="Nominate a new option!"
            name="incentiveBidNewOption"
            checked={customOptionSelected}
            look={Checkbox.Looks.DENSE}
            onChange={handleNewChoice(null)}
          />
          {customOptionSelected && (
            <TextInput
              value={customOption}
              name="incentiveBidCustomOption"
              placeholder="Enter Option Here"
              onChange={setCustomOption}
              maxLength={incentive.option_max_length ?? undefined}
            />
          )}
        </>
      )}

      <ErrorAlert errors={bidValidation} />

      <Button
        disabled={bidValidation != null}
        fullwidth
        onClick={handleSubmitBid}
        data-testid="incentiveBidForm-submitBid">
        Add
      </Button>
    </div>
  );
};

export default DonationBidForm;
