import React from 'react';
import { shallowEqual } from 'react-redux';
import { useLocation } from 'react-router';

import { useConstants } from '@common/Constants';
import APIErrorList from '@public/APIErrorList';
import { DonationPostBid } from '@public/apiv2/APITypes';
import {
  useBidTreeQuery,
  useDonateMutation,
  useDonatePreflightQuery,
  useEventFromRoute,
  usePrizesQuery,
} from '@public/apiv2/hooks';
import { Event } from '@public/apiv2/Models';
import { RecursiveRecord } from '@public/apiv2/reducers/trackerBaseApi';
import { useCachedCallback } from '@public/hooks/useCachedCallback';
import * as CurrencyUtils from '@public/util/currency';
import { useEventCurrency } from '@public/util/currency';
import { hasItems } from '@public/util/Types';
import Anchor from '@uikit/Anchor';
import Button from '@uikit/Button';
import Checkbox from '@uikit/Checkbox';
import Container from '@uikit/Container';
import CurrencyInput from '@uikit/CurrencyInput';
import ErrorAlert from '@uikit/ErrorAlert';
import Header from '@uikit/Header';
import LoadingDots from '@uikit/LoadingDots';
import Text from '@uikit/Text';
import TextInput from '@uikit/TextInput';

import validateDonation, { DonationFormEntry } from '@tracker/donation/validateDonation';

import { AnalyticsEvent, track } from '../../analytics/Analytics';
import DonationIncentives from './DonationIncentives';
import DonationPrizes from './DonationPrizes';

import styles from './Donate.mod.css';

const AMOUNT_PRESETS = [25, 50, 75, 100, 250, 500];

function Internal({ event }: { event: Event }) {
  const { PRIVACY_POLICY_URL, SWEEPSTAKES_URL, PAYPAL_MAXIMUM_AMOUNT } = useConstants();
  const { data: prizes, ...prizesState } = usePrizesQuery(
    { urlParams: { eventId: event.id, feed: 'current' } },
    { pollingInterval: 300000 },
  );
  const { data: bids, ...bidsState } = useBidTreeQuery({ urlParams: { eventId: event.id, feed: 'open' } });
  const [donation, setDonation] = React.useState<DonationFormEntry>({
    requested_email: '',
    requested_alias: '',
    comment: '',
    bids: [],
    email_optin: false,
    domain: 'PAYPAL',
  });
  const [donate, donateState] = useDonateMutation();
  const reset = React.useCallback(() => donateState.reset(), [donateState]);

  const eventCurrency = useEventCurrency();

  const urlHash = useLocation().hash;
  React.useEffect(() => {
    const presetAmount = CurrencyUtils.parseCurrency(urlHash);
    if (presetAmount != null) {
      setDonation(donation => (donation.amount == null ? { ...donation, amount: presetAmount } : donation));
    }
  }, [urlHash]);

  const tracked = React.useRef(false);

  React.useEffect(() => {
    if (prizes && bids && !tracked.current) {
      track(AnalyticsEvent.DONATE_FORM_VIEWED, {
        event_url_id: event.id,
        prize_count: prizes.length,
        bid_count: bids.length,
      });
      tracked.current = true;
    }
  }, [bids, event, prizes]);

  const errors = validateDonation(event, donation, PAYPAL_MAXIMUM_AMOUNT);

  const allErrors = React.useMemo(() => {
    let allErrors: RecursiveRecord | null = null;
    if (errors?.status === 400) {
      allErrors = errors.data as RecursiveRecord;
    }
    return allErrors;
  }, [errors]);

  const [confirmUrl, setConfirmUrl] = React.useState('');
  const confirmRef = React.useRef<HTMLFormElement | null>(null);
  React.useEffect(() => {
    if (confirmUrl && confirmRef.current) {
      confirmRef.current.submit();
    }
  }, [confirmUrl]);

  const handleSubmit = React.useCallback(async () => {
    if (errors == null && donation.amount) {
      const { data } = await donate({ ...donation, amount: donation.amount, event: event.id });
      if (data?.confirm_url) {
        const url = new URL(data.confirm_url, window.location.origin);
        if (url.origin === window.location.origin) {
          setConfirmUrl(url.toString());
        } else {
          // this is a serious misconfiguration issue
          throw new Error(
            `confirmation url and window url origin did not match: ${url.origin} !== ${window.location.origin}`,
          );
        }
      } else {
        bidsState.refetch();
      }
    }
  }, [errors, donation, donate, event.id, bidsState]);

  const updateName = React.useCallback(
    (name: string) => setDonation(donation => ({ ...donation, requested_alias: name })),
    [],
  );
  const updateEmail = React.useCallback(
    (email: string) => setDonation(donation => ({ ...donation, requested_email: email })),
    [],
  );
  const toggleWantsEmails = React.useCallback(
    () => setDonation(donation => ({ ...donation, email_optin: !donation.email_optin })),
    [],
  );
  const updateAmount = React.useCallback((amount: number) => {
    setDonation(donation => ({ ...donation, amount }));
  }, []);
  const updateAmountPreset = useCachedCallback(amount => setDonation(donation => ({ ...donation, amount })), []);
  const updateComment = React.useCallback((comment: string) => setDonation(donation => ({ ...donation, comment })), []);
  const addBid = React.useCallback(
    (bid: DonationPostBid) =>
      setDonation(donation => ({
        ...donation,
        bids: [...donation.bids, bid],
      })),
    [],
  );
  const deleteBid = React.useCallback(
    (bid: DonationPostBid) =>
      setDonation(donation => ({
        ...donation,
        bids: donation.bids.filter(b => !shallowEqual(b, bid)),
      })),
    [],
  );

  if (!event.allow_donations) {
    return (
      <Container>
        <Header>{event.name} is not currently accepting donations.</Header>
      </Container>
    );
  }

  return (
    <Container>
      {<form style={{ display: 'none' }} ref={confirmRef} action={confirmUrl} method="post" />}
      <Header size={Header.Sizes.H1} marginless>
        Thank You For Your Donation
      </Header>
      <Text size={Text.Sizes.SIZE_16}>100% of your donation goes directly to {event.receivername}.</Text>
      <section className={styles.section}>
        <ErrorAlert errors={allErrors?.comment} />
        <TextInput
          name="alias"
          value={donation.requested_alias}
          label="Preferred Name/Alias"
          hint="Leave blank to donate anonymously"
          size={TextInput.Sizes.LARGE}
          onChange={updateName}
          maxLength={32}
          autoFocus
        />
        <ErrorAlert errors={allErrors?.email} />
        <TextInput
          name="email"
          value={donation.requested_email}
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

        <Checkbox
          checked={donation.email_optin}
          onChange={toggleWantsEmails}
          label={
            <Text size={Text.Sizes.SIZE_14}>
              {event.receiver_solicitation_text || `Check here to receive emails from ${event.receivername}`}
            </Text>
          }>
          {event.receiver_privacy_policy && (
            <Text size={Text.Sizes.SIZE_12}>
              Click <Anchor href={event.receiver_privacy_policy}>here</Anchor> for the privacy policy for{' '}
              {event.receivername}
            </Text>
          )}
        </Checkbox>

        <ErrorAlert errors={donation.amount != null ? allErrors?.amount : null} />

        <CurrencyInput
          name="amount"
          value={donation.amount}
          label="Amount"
          currency={event?.paypalcurrency}
          hint={
            <React.Fragment>
              Minimum donation is<strong> {eventCurrency(event.minimumdonation)}</strong>
              <br />
              Maximum donation is
              <strong> {eventCurrency(event.maximum_paypal_donation ?? PAYPAL_MAXIMUM_AMOUNT)}</strong>
            </React.Fragment>
          }
          size={CurrencyInput.Sizes.LARGE}
          onChange={updateAmount}
          step={0.01}
          min={event.minimumdonation}
          max={event.maximum_paypal_donation ?? PAYPAL_MAXIMUM_AMOUNT}
        />
        <div className={styles.amountPresets}>
          {AMOUNT_PRESETS.map(amountPreset => (
            <Button
              className={styles.amountPreset}
              key={amountPreset}
              look={Button.Looks.OUTLINED}
              onClick={updateAmountPreset(amountPreset)}>
              {eventCurrency(amountPreset)}
            </Button>
          ))}
        </div>

        <ErrorAlert errors={allErrors?.comment} />

        <TextInput
          name="comment"
          value={donation.comment}
          label="Leave a Comment?"
          placeholder="Enter Comment Here"
          hint="Please refrain from offensive language or hurtful remarks. All donation comments are screened and will be removed from the website if deemed unacceptable."
          multiline
          onChange={updateComment}
          maxLength={5000}
          rows={5}
        />
      </section>
      {prizesState.isLoading ? (
        <LoadingDots />
      ) : (
        hasItems(prizes) &&
        SWEEPSTAKES_URL && (
          <section className={styles.section}>
            <DonationPrizes prizes={prizes} />
          </section>
        )
      )}
      {bidsState.isLoading ? (
        <LoadingDots />
      ) : (
        hasItems(bids) && (
          <section className={styles.section}>
            <ErrorAlert errors={allErrors?.bids} />
            <Header size={Header.Sizes.H3}>Incentives</Header>
            <Text>
              Donation incentives can be used to add bonus runs to the schedule and influence choices by runners. Would
              you like to put your donation towards an incentive?
            </Text>
            <DonationIncentives
              className={styles.incentives}
              donation={donation}
              bids={bids}
              addBid={addBid}
              deleteBid={deleteBid}
            />
          </section>
        )
      )}
      <section className={styles.section}>
        <Header size={Header.Sizes.H3}>Donate!</Header>
        <ErrorAlert errors={allErrors} />
        <APIErrorList errors={donateState.error} reset={reset} />
        <Button
          size={Button.Sizes.LARGE}
          disabled={errors != null || donateState.isLoading}
          fullwidth
          onClick={handleSubmit}
          data-testid="donation-submit">
          Donate {eventCurrency(donation.amount ?? 0)}
        </Button>
      </section>
      {event.receiver_logo && (
        <section className={styles.section}>
          <img style={{ width: '100%' }} alt={event.receivername} src={event.receiver_logo} />
        </section>
      )}
    </Container>
  );
}

export default function Donate() {
  useDonatePreflightQuery();
  const { data } = useEventFromRoute();

  return data ? <Internal event={data} /> : <LoadingDots />;
}
