import React from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';
import _ from 'lodash';
import cn from 'classnames';

import * as CurrencyUtils from '../../../public/util/currency';
import Anchor from '../../../uikit/Anchor';
import Button from '../../../uikit/Button';
import Header from '../../../uikit/Header';
import RadioGroup from '../../../uikit/RadioGroup';
import Text from '../../../uikit/Text';
import TextInput from '../../../uikit/TextInput';
import Incentives from '../../incentives/components/Incentives';
import * as EventDetailsStore from '../../event_details/EventDetailsStore';
import * as DonationActions from '../DonationActions';
import { EMAIL_OPTIONS, AMOUNT_PRESETS } from '../DonationConstants';
import * as DonationStore from '../DonationStore';
import DonationPrizes from './DonationPrizes';

import styles from './DonationForm.mod.css';

class DonationForm extends React.PureComponent {
  static propTypes = {
    formErrors: PropTypes.shape({
      bidsform: PropTypes.array.isRequired,
      commentform: PropTypes.object.isRequired,
    }).isRequired,
    initialIncentives: PropTypes.arrayOf(
      PropTypes.shape({
        bid: PropTypes.number, // will be null if the bid closed while we were filling it out
        amount: PropTypes.string.isRequired,
        customoptionname: PropTypes.string.isRequired,
      }).isRequired,
    ).isRequired,
    prizes: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number.isRequired,
        description: PropTypes.string,
        minimumbid: PropTypes.string.isRequired,
        name: PropTypes.string.isRequired,
      }).isRequired,
    ).isRequired,
    csrfToken: PropTypes.string,
    onSubmit: PropTypes.func,
  };

  static defaultProps = {
    initialIncentives: [],
  };

  state = {
    showIncentives: this.props.initialIncentives.length !== 0,
    currentIncentives: this.props.initialIncentives || [],
  };

  sumIncentives_() {
    return this.state.currentIncentives.reduce((sum, ci) => (ci.bid ? sum + +ci.amount : 0), 0);
  }

  updateDonation = (fields = {}) => {
    const { dispatch } = this.props;
    dispatch(DonationActions.updateDonation(fields));
  };

  cannotSubmit_() {
    const { amount, currentIncentives, showIncentives } = this.state;
    const { minimumDonation, incentives } = this.props;
    if (currentIncentives.length > 10) {
      return 'Too many incentives.';
    }
    if (this.sumIncentives_() > amount) {
      return 'Total bid amount cannot exceed donation amount.';
    }
    if (showIncentives && this.sumIncentives_() < amount) {
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
  }

  render() {
    const { formErrors, prizes, incentives, eventDetails, donation, csrfToken, onSubmit } = this.props;
    const { showIncentives } = this.state;
    const { receiverName, donateUrl, prizesUrl, rulesUrl, minimumDonation, maximumDonation, step } = eventDetails;
    const { name, nameVisibility, email, wantsEmails, amount, comment } = donation;

    // TODO: show more form errors
    const cannotSubmit = this.cannotSubmit_();

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
            onChange={name => this.updateDonation({ name })}
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
            onChange={email => this.updateDonation({ email })}
          />

          <Text size={Text.Sizes.SIZE_16} marginless>
            Do you want to receive emails from {receiverName}?
          </Text>
          <div className={styles.emailButtons}>
            <RadioGroup
              className={styles.emailOptin}
              options={EMAIL_OPTIONS}
              value={wantsEmails}
              onChange={value => this.updateDonation({ wantsEmails: value })}
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
            onChange={amount => this.updateDonation({ amount })}
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
                onClick={() => this.updateDonation({ amount: amountPreset })}>
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
            onChange={comment => this.updateDonation({ comment })}
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
            Donation incentives can be used to add bonus runs to the schedule and influence choices by runners. Would
            you like to put your donation towards an incentive?
          </Text>
          {showIncentives ? (
            <Incentives className={styles.incentives} step={step} total={(amount || 0) - this.sumIncentives_()} />
          ) : (
            <Button
              disabled={showIncentives}
              look={Button.Looks.OUTLINED}
              fullwidth
              onClick={() => this.setState({ showIncentives: true })}>
              Add Incentives
            </Button>
          )}
        </section>

        <section className={styles.section}>
          <Header size={Header.Sizes.H3}>Donate!</Header>
          {cannotSubmit && <Text>{cannotSubmit}</Text>}
          <Button size={Button.Sizes.LARGE} disabled={cannotSubmit} fullwidth type="submit">
            Finish
          </Button>
        </section>
      </form>
    );
  }
}

const mapStateToProps = state => {
  return {
    eventDetails: EventDetailsStore.getEventDetails(state),
    donation: DonationStore.getDonation(state),
  };
};

export default connect(mapStateToProps)(DonationForm);
