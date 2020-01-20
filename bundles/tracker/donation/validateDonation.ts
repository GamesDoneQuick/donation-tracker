import _ from 'lodash';
import validator from 'validator';

import * as CurrencyUtils from '../../public/util/currency';
import { EventDetails } from '../event_details/EventDetailsTypes';
import { MAX_BIDS_PER_DONATION } from './DonationConstants';
import { Bid, Donation, Validation } from './DonationTypes';

export const DonationErrors = {
  NO_AMOUNT: 'Donation amount is not set',

  AMOUNT_MINIMUM: (min: number) => `Donation amount is below the allowed minimum (${CurrencyUtils.asCurrency(min)})`,
  AMOUNT_MAXIMUM: (max: number) => `Donation amount is above the allowed maximum (${CurrencyUtils.asCurrency(max)})`,

  TOO_MANY_BIDS: (maxBids: number) => `Only ${maxBids} bids can be set per donation.`,
  BID_SUM_EXCEEDS_TOTAL: 'Sum of bid amounts exceeds donation total.',

  INVALID_EMAIL: 'Email is not a valid email address',
};

export default function validateDonation(eventDetails: EventDetails, donation: Donation, bids: Bid[]): Validation {
  const sumOfBids = _.sumBy(bids, 'amount');
  const errors = [];

  if (donation.amount == null) {
    errors.push({ field: 'amount', message: DonationErrors.NO_AMOUNT });
  } else {
    if (donation.amount < eventDetails.minimumDonation) {
      errors.push({
        field: 'amount',
        message: DonationErrors.AMOUNT_MINIMUM(eventDetails.minimumDonation),
      });
    }

    if (donation.amount > eventDetails.maximumDonation) {
      errors.push({
        field: 'amount',
        message: DonationErrors.AMOUNT_MAXIMUM(eventDetails.maximumDonation),
      });
    }

    if (bids.length > MAX_BIDS_PER_DONATION) {
      errors.push({ field: 'bids', message: DonationErrors.TOO_MANY_BIDS(MAX_BIDS_PER_DONATION) });
    }

    if (bids.length > 0) {
      if (sumOfBids > donation.amount) {
        errors.push({ field: 'bids', message: DonationErrors.BID_SUM_EXCEEDS_TOTAL });
      }
    }
  }

  if (donation.email !== '' && !validator.isEmail(donation.email)) {
    errors.push({ field: 'email', message: DonationErrors.INVALID_EMAIL });
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}
