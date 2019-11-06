import React from 'react';
import PropTypes from 'prop-types';
import { connect, useDispatch, useSelector } from 'react-redux';
import _ from 'lodash';
import cn from 'classnames';

import * as CurrencyUtils from '../../../public/util/currency';
import Anchor from '../../../uikit/Anchor';
import Button from '../../../uikit/Button';
import Header from '../../../uikit/Header';
import RadioGroup from '../../../uikit/RadioGroup';
import Text from '../../../uikit/Text';
import TextInput from '../../../uikit/TextInput';
import * as IncentiveStore from '../../incentives/IncentiveStore';
import Incentives from '../../incentives/components/Incentives';
import * as EventDetailsStore from '../../event_details/EventDetailsStore';
import * as DonationActions from '../DonationActions';
import { EMAIL_OPTIONS, AMOUNT_PRESETS } from '../DonationConstants';
import * as DonationStore from '../DonationStore';
import DonationPrizes from './DonationPrizes';

import styles from './DonationForm.mod.css';

type Incentive = {
  bid?: number;
  amount: string;
  customoptionname: string;
};

type DonationFormProps = {
  prizes: Array<{
    id: number;
    description?: string;
    minimumbid: string;
    name: string;
  }>;
  csrfToken: string;
  onSubmit: () => void;
};

type DonationFormState = {
  showIncentives: boolean;
  currentIncentives: Array<Incentive>;
};

const DonationForm = (props: DonationFormProps) => {
  const dispatch = useDispatch();
  const { prizes, csrfToken, onSubmit } = props;

  const { eventDetails, donation, incentives } = useSelector(state => ({
    eventDetails: EventDetailsStore.getEventDetails(state),
    donation: DonationStore.getDonation(state),
    incentives: IncentiveStore.getIncentives(state),
  }));

  const { receiverName, donateUrl, prizesUrl, rulesUrl, minimumDonation, maximumDonation, step } = eventDetails;
  const { name, nameVisibility, email, wantsEmails, amount, comment } = donation;

  const [showIncentives, setShowIncentives] = React.useState(false);
  const [currentIncentives, setCurrentIncentives] = React.useState<Array<Incentive>>([]);

  const sumOfIncentives = React.useMemo(
    () => currentIncentives.reduce((sum, ci) => (ci.bid ? sum + +ci.amount : 0), 0),
    [currentIncentives],
  );

  const cannotSubmit = React.useMemo(() => {
    if (currentIncentives.length > 10) {
      return 'Too many incentives.';
    }
    if (sumOfIncentives > amount) {
      return 'Total bid amount cannot exceed donation amount.';
    }
    if (showIncentives && sumOfIncentives < amount) {
      return 'Total donation amount not allocated.';
    }
    if (amount < minimumDonation) {
      return 'Donation amount below minimum.';
    }
    if (
      currentIncentives.some(ci => {
        const incentive = incentives.find(i => i.id === ci.bid);
        return incentive && incentive.maxlength && ci.customoptionname.length > incentive.maxlength;
      })
    ) {
      return 'Suggestion is too long.';
    }
    return null;
  }, [showIncentives, currentIncentives, sumOfIncentives, amount, minimumDonation, incentives]);

  const updateDonation = React.useCallback(
    (fields = {}) => {
      dispatch(DonationActions.updateDonation(fields));
    },
    [dispatch],
  );

  return (
    <form className={styles.donationForm} action={donateUrl} method="post" onSubmit={onSubmit}>
      <Header size={Header.Sizes.H1} marginless>
        Thank You For Your Donation
      </Header>
      <Text size={Text.Sizes.SIZE_16}>100% of your donation goes directly to {receiverName}.</Text>

      <section className={styles.section}>
        <TextInput
          name="requestedalias"
          value={name}
          label="Preferred Name/Alias"
          hint="Leave blank to donate anonymously"
          size={TextInput.Sizes.LARGE}
          onChange={name => updateDonation({ name })}
          maxLength={32}
          autoFocus
        />
        <TextInput
          name="requestedemail"
          value={email}
          label="Email Address"
          hint={
            <React.Fragment>
              Click{' '}
              <Anchor href="https://gamesdonequick.com/privacy/" external newTab>
                here
              </Anchor>{' '}
              for our privacy policy
            </React.Fragment>
          }
          size={TextInput.Sizes.LARGE}
          type={TextInput.Types.EMAIL}
          onChange={email => updateDonation({ email })}
        />

        <Text size={Text.Sizes.SIZE_16} marginless>
          Do you want to receive emails from {receiverName}?
        </Text>
        <div className={styles.emailButtons}>
          <RadioGroup
            className={styles.emailOptin}
            options={EMAIL_OPTIONS}
            value={wantsEmails}
            onChange={value => updateDonation({ wantsEmails: value })}
          />
        </div>

        <TextInput
          name="amount"
          value={amount || ''}
          label="Amount"
          leader="$"
          placeholder="0.00"
          hint={
            <React.Fragment>
              Minimum donation is <strong>{CurrencyUtils.asCurrency(minimumDonation)}</strong>
            </React.Fragment>
          }
          size={TextInput.Sizes.LARGE}
          type={TextInput.Types.NUMBER}
          onChange={amount => updateDonation({ amount })}
          step={step}
          min={minimumDonation}
          max={maximumDonation}
        />
        <div className={styles.amountPresets}>
          {AMOUNT_PRESETS.map(amountPreset => (
            <Button
              className={styles.amountPreset}
              key={amountPreset}
              look={Button.Looks.OUTLINED}
              onClick={() => updateDonation({ amount: amountPreset })}>
              ${amountPreset}
            </Button>
          ))}
        </div>

        <TextInput
          name="comment"
          value={comment}
          label="Leave a Comment?"
          placeholder="Enter Comment Here"
          hint="Please refrain from offensive language or hurtful remarks. All donation comments are screened and will be removed from the website if deemed unacceptable."
          multiline
          onChange={comment => updateDonation({ comment })}
          maxLength={5000}
          rows={5}
        />
      </section>

      {prizes.length > 0 && (
        <section className={styles.section}>
          <DonationPrizes prizes={prizes} prizesURL={prizesUrl} rulesURL={rulesUrl} />
        </section>
      )}

      <section className={styles.section}>
        <Header size={Header.Sizes.H3}>Incentives</Header>
        <Text>
          Donation incentives can be used to add bonus runs to the schedule and influence choices by runners. Would you
          like to put your donation towards an incentive?
        </Text>
        {showIncentives ? (
          <Incentives className={styles.incentives} step={step} total={(amount || 0) - sumOfIncentives} />
        ) : (
          <Button
            disabled={showIncentives}
            look={Button.Looks.OUTLINED}
            fullwidth
            onClick={() => setShowIncentives(true)}>
            Add Incentives
          </Button>
        )}
      </section>

      <section className={styles.section}>
        <Header size={Header.Sizes.H3}>Donate!</Header>
        {cannotSubmit && <Text>{cannotSubmit}</Text>}
        <Button size={Button.Sizes.LARGE} disabled={!!cannotSubmit} fullwidth>
          Finish
        </Button>
      </section>
    </form>
  );
};

export default DonationForm;
