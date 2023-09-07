import React from 'react';
import { useSelector } from 'react-redux';

import { useConstants } from '@common/Constants';
import { useCachedCallback } from '@public/hooks/useCachedCallback';
import * as CurrencyUtils from '@public/util/currency';
import Anchor from '@uikit/Anchor';
import Button from '@uikit/Button';
import Container from '@uikit/Container';
import CurrencyInput from '@uikit/CurrencyInput';
import ErrorAlert from '@uikit/ErrorAlert';
import Header from '@uikit/Header';
import RadioGroup from '@uikit/RadioGroup';
import Text from '@uikit/Text';
import TextInput from '@uikit/TextInput';

import * as EventDetailsStore from '@tracker/event_details/EventDetailsStore';
import useDispatch from '@tracker/hooks/useDispatch';
import RouterUtils from '@tracker/router/RouterUtils';
import { StoreState } from '@tracker/Store';

import { AnalyticsEvent, track } from '../../analytics/Analytics';
import * as DonationActions from '../DonationActions';
import { AMOUNT_PRESETS, EMAIL_OPTIONS } from '../DonationConstants';
import * as DonationStore from '../DonationStore';
import DonationIncentives from './DonationIncentives';
import DonationPrizes from './DonationPrizes';

import styles from './Donate.mod.css';

type DonateProps = {
  eventId: string | number;
};

const Donate = (props: DonateProps) => {
  const { PRIVACY_POLICY_URL } = useConstants();
  const dispatch = useDispatch();
  const { eventId } = props;

  const urlHash = RouterUtils.getLocationHash();
  React.useEffect(() => {
    const presetAmount = CurrencyUtils.parseCurrency(urlHash);
    if (presetAmount != null) {
      dispatch(DonationActions.updateDonation({ amount: presetAmount }));
    }
  }, [dispatch, urlHash]);

  const { eventDetails, prizes, donation, bids, commentErrors, donationValidity } = useSelector(
    (state: StoreState) => ({
      eventDetails: EventDetailsStore.getEventDetails(state),
      prizes: EventDetailsStore.getPrizes(state),
      donation: DonationStore.getDonation(state),
      bids: DonationStore.getBids(state),
      commentErrors: DonationStore.getCommentFormErrors(state),
      donationValidity: DonationStore.validateDonation(state),
    }),
  );

  React.useEffect(() => {
    track(AnalyticsEvent.DONATE_FORM_VIEWED, {
      event_url_id: eventId,
      prize_count: prizes.length,
      bid_count: bids.length,
    });
    // Only want to fire this event when the context of the page changes, not when data updates.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventId]);

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

  const updateName = React.useCallback((name: string) => updateDonation({ name }), [updateDonation]);
  const updateEmail = React.useCallback((email: string) => updateDonation({ email }), [updateDonation]);
  const updateWantsEmails = React.useCallback(
    (value: 'CURR' | 'OPTIN' | 'OPTOUT') => updateDonation({ wantsEmails: value }),
    [updateDonation],
  );
  const updateAmount = React.useCallback((amount: number) => updateDonation({ amount }), [updateDonation]);
  const updateAmountPreset = useCachedCallback(
    amountPreset => updateDonation({ amount: amountPreset }),
    [updateDonation],
  );
  const updateComment = React.useCallback((comment: string) => updateDonation({ comment }), [updateDonation]);

  return (
    <Container>
      <ErrorAlert errors={commentErrors.__all__} />
      <Header size={Header.Sizes.H1} marginless>
        Thank You For Your Donation
      </Header>
      <Text size={Text.Sizes.SIZE_16}>100% of your donation goes directly to {receiverName}.</Text>

      <section className={styles.section}>
        <ErrorAlert errors={commentErrors.requestedalias} />
        <TextInput
          name="alias"
          value={name}
          label="Preferred Name/Alias"
          hint="Leave blank to donate anonymously"
          size={TextInput.Sizes.LARGE}
          onChange={updateName}
          maxLength={32}
          autoFocus
        />
        <ErrorAlert errors={commentErrors.requestedemail} />
        <TextInput
          name="email"
          value={email}
          label="Email Address"
          hint={
            PRIVACY_POLICY_URL && (
              <>
                Click <Anchor href={PRIVACY_POLICY_URL}>here</Anchor> for our privacy policy
              </>
            )
          }
          size={TextInput.Sizes.LARGE}
          type={TextInput.Types.EMAIL}
          onChange={updateEmail}
          maxLength={128}
        />

        <ErrorAlert errors={commentErrors.requestedsolicitemail} />

        <Text size={Text.Sizes.SIZE_16} marginless>
          Do you want to receive emails from {receiverName}?
        </Text>

        <RadioGroup
          className={styles.emailOptin}
          options={EMAIL_OPTIONS}
          value={wantsEmails}
          onChange={updateWantsEmails}
        />

        <ErrorAlert errors={commentErrors.amount} />

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
          onChange={updateAmount}
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
              onClick={updateAmountPreset(amountPreset)}>
              ${amountPreset}
            </Button>
          ))}
        </div>

        <ErrorAlert errors={commentErrors.comment} />

        <TextInput
          name="comment"
          value={comment}
          label="Leave a Comment?"
          placeholder="Enter Comment Here"
          hint="Please refrain from offensive language or hurtful remarks. All donation comments are screened and will be removed from the website if deemed unacceptable."
          multiline
          onChange={updateComment}
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
