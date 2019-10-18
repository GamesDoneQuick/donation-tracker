import * as React from 'react';
import {useDispatch, useSelector} from 'react-redux';
import classNames from 'classnames';

import * as CurrencyUtils from '../../../public/util/currency';
import Button from '../../../uikit/Button';
import Checkbox from '../../../uikit/Checkbox';
import Header from '../../../uikit/Header';
import ProgressBar from '../../../uikit/ProgressBar';
import Text from '../../../uikit/Text';
import TextInput from '../../../uikit/TextInput';
import * as IncentiveActions from '../IncentiveActions';
import * as IncentiveStore from '../IncentiveStore';
import * as IncentiveUtils from '../IncentiveUtils';

import styles from './IncentiveBidForm.mod.css';

const BidForm = (props) => {
  const {
    incentiveId,
    step,
    total: donationTotal,
    className,
  } = props;

  const dispatch = useDispatch();

  const {incentive, bidChoices, allocatedTotal} = useSelector((state) => ({
    incentive: IncentiveStore.getIncentive(state, incentiveId),
    bidChoices: IncentiveStore.getChildIncentives(state, incentiveId),
    allocatedTotal: IncentiveStore.getAllocatedBidTotal(state),
  }));

  const remainingDonationTotal = donationTotal - allocatedTotal;
  const remainingDonationTotalString = CurrencyUtils.asCurrency(remainingDonationTotal);

  const [allocatedAmount, setAllocatedAmount] = React.useState(remainingDonationTotal);
  const [selectedChoiceId, setSelectedChoiceId] = React.useState(null);
  const [customOptionSelected, setCustomOptionSelected] = React.useState(false);
  const [customOption, setCustomOption] = React.useState("");

  const [bidIsValid, bidErrorText] = React.useMemo(() => (
    IncentiveUtils.validateBid({
      amount: allocatedAmount,
      donationTotal,
      incentive,
      choice: selectedChoiceId,
      customOption,
    })
  ), [allocatedAmount, donationTotal, incentive, customOption]);

  const handleNewChoice = React.useCallback((choiceId) => {
    setSelectedChoiceId(choiceId);
    setCustomOptionSelected(choiceId == null);
  }, []);

  const handleSubmitBid = React.useCallback(() => {
    dispatch(IncentiveActions.createBid({
      incentiveId: selectedChoiceId != null ? selectedChoiceId : incentive.id,
      customOption,
      amount: allocatedAmount,
    }));
  }, [dispatch, incentive, selectedChoiceId, allocatedAmount, customOption]);


  if(incentive == null) {
    return (
      <div className={classNames(styles.container, className)}>
        <Text>You have {remainingDonationTotalString} remaining.</Text>
      </div>
    );
  }

  const goalProgress = incentive.amount / incentive.goal * 100;

  return (
    <div className={classNames(styles.container, className)}>
      <Header size={Header.Sizes.H4}>{incentive.runname}</Header>
      <Header size={Header.Sizes.H5}>{incentive.name}</Header>
      <Text size={Text.Sizes.SIZE_14}>{incentive.description}</Text>

      { incentive.goal &&
        <React.Fragment>
          <ProgressBar className={styles.progressBar} progress={goalProgress} />
          <Text marginless>Current Raised Amount: <span>{CurrencyUtils.asCurrency(incentive.amount)} / {CurrencyUtils.asCurrency(incentive.goal)}</span></Text>
        </React.Fragment>
      }

      <TextInput
        value={allocatedAmount}
        type={TextInput.Types.NUMBER}
        label="Amount to put towards incentive"
        hint={<React.Fragment>You have <strong>{remainingDonationTotalString}</strong> remaining.</React.Fragment>}
        leader="$"
        onChange={setAllocatedAmount}
        step={step}
        min={0}
        max={remainingDonationTotal}
      />

      { bidChoices.length > 0
        ? bidChoices.map(choice => (
            <Checkbox
                key={choice.id}
                checked={selectedChoiceId === choice.id}
                contentClassName={styles.choiceLabel}
                look={Checkbox.Looks.DENSE}
                onChange={() => handleNewChoice(choice.id)}>
              <Checkbox.Header>{choice.name}</Checkbox.Header>
              <span className={styles.choiceAmount}>${choice.amount}</span>
            </Checkbox>
          ))
        : null
      }

      { incentive.custom
        ? <Checkbox
              label="Nominate a new option!"
              checked={customOptionSelected}
              look={Checkbox.Looks.NORMAL}
              onChange={() => handleNewChoice(null)}>
            <TextInput
              value={customOption}
              disabled={!customOptionSelected}
              placeholder="Enter Option Here"
              onChange={setCustomOption}
              maxLength={incentive.maxlength}
            />
          </Checkbox>
        : null
      }

      <Button disabled={!bidIsValid} fullwidth onClick={handleSubmitBid}>Add</Button>
      {bidErrorText && <Text marginless>{bidErrorText}</Text>}
    </div>
  );
};

export default BidForm;
