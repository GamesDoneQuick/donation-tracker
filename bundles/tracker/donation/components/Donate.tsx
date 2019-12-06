import React from 'react';
import PropTypes from 'prop-types';
import { useSelector } from 'react-redux';
import _ from 'lodash';

import * as CurrencyUtils from '../../../public/util/currency';
import Alert from '../../../uikit/Alert';
import Anchor from '../../../uikit/Anchor';
import Button from '../../../uikit/Button';
import Container from '../../../uikit/Container';
import CurrencyInput from '../../../uikit/CurrencyInput';
import Header from '../../../uikit/Header';
import RadioGroup from '../../../uikit/RadioGroup';
import Text from '../../../uikit/Text';
import TextInput from '../../../uikit/TextInput';
import useDispatch from '../../hooks/useDispatch';
import * as EventDetailsStore from '../../event_details/EventDetailsStore';
import { StoreState } from '../../Store';
import * as DonationActions from '../DonationActions';
import * as DonationStore from '../DonationStore';
import DonationIncentives from './DonationIncentives';
import DonationPrizes from './DonationPrizes';

import { EMAIL_OPTIONS, AMOUNT_PRESETS } from '../DonationConstants';
import styles from './Donate.mod.css';

type DonateProps = {
  eventId: string | number;
};

const Donate = (props: DonateProps) => {
  const dispatch = useDispatch();
  const { eventId } = props;

  const { eventDetails, prizes, donation, bids, donationValidity, formError } = useSelector((state: StoreState) => ({
    eventDetails: EventDetailsStore.getEventDetails(state),
    prizes: EventDetailsStore.getPrizes(state),
    donation: DonationStore.getDonation(state),
    bids: DonationStore.getBids(state),
    formError: DonationStore.getFormError(state),
    donationValidity: DonationStore.validateDonation(state),
  }));

  const { receiverName, donateUrl, minimumDonation, maximumDonation, step } = eventDetails;
  const { name, email, wantsEmails, amount, comment } = donation;

  const updateDonation = React.useCallback(
    (fields = {}) => {
      dispatch(DonationActions.updateDonation(fields));
    },
    [dispatch],
  );

  const handleSubmit = React.useCallback(() => {
    if (donationValidity.valid) {
      DonationActions.submitDonation(donateUrl, eventDetails.csrfToken, donation, bids);
    }
  }, [donateUrl, eventDetails.csrfToken, donation, bids, donationValidity]);

  return (
    <Container>
      {formError != null ? (
        <Alert className={styles.alert}>
          <Text marginless>{formError}</Text>
        </Alert>
      ) : null}
      <Header size={Header.Sizes.H1} marginless>
        Thank You For Your Donation
      </Header>
      <Text size={Text.Sizes.SIZE_16}>100% of your donation goes directly to {receiverName}.</Text>

      <section className={styles.section}>
        <TextInput
          name="alias"
          value={name}
          label="Preferred Name/Alias"
          hint="Leave blank to donate anonymously"
          size={TextInput.Sizes.LARGE}
          onChange={name => updateDonation({ name })}
          maxLength={32}
          autoFocus
        />
        <TextInput
          name="email"
          value={email}
          label="Email Address"
          hint={
            <React.Fragment>
              Click <Anchor href="https://gamesdonequick.com/privacy/">here</Anchor> for our privacy policy
            </React.Fragment>
          }
          size={TextInput.Sizes.LARGE}
          type={TextInput.Types.EMAIL}
          onChange={email => updateDonation({ email })}
          maxLength={128}
        />

        <Text size={Text.Sizes.SIZE_16} marginless>
          Do you want to receive emails from {receiverName}?
        </Text>

        <RadioGroup
          className={styles.emailOptin}
          options={EMAIL_OPTIONS}
          value={wantsEmails}
          onChange={value => updateDonation({ wantsEmails: value })}
        />

        <CurrencyInput
          name="amount"
          value={amount}
          label="Amount"
          hint={
            <React.Fragment>
              Minimum donation is <strong>{CurrencyUtils.asCurrency(minimumDonation)}</strong>
            </React.Fragment>
          }
          size={CurrencyInput.Sizes.LARGE}
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
          <DonationPrizes eventId={eventId} />
        </section>
      )}

      <section className={styles.section}>
        <Header size={Header.Sizes.H3}>Incentives</Header>
        <Text>
          Donation incentives can be used to add bonus runs to the schedule and influence choices by runners. Would you
          like to put your donation towards an incentive?
        </Text>
        <DonationIncentives className={styles.incentives} step={step} total={amount != null ? amount : 0} />
      </section>

      <section className={styles.section}>
        <Header size={Header.Sizes.H3}>Donate!</Header>
        {!donationValidity.valid && <Text>{donationValidity.errors.map(error => error.message)}</Text>}
        <Button
          size={Button.Sizes.LARGE}
          disabled={!donationValidity.valid}
          fullwidth
          onClick={handleSubmit}
          data-testid="donation-submit">
          Donate {amount != null ? CurrencyUtils.asCurrency(amount) : null}
        </Button>
      </section>
    </Container>
  );
};

export default Donate;
