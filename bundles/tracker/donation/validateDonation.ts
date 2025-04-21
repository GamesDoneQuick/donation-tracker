import validator from 'validator';

import { DonationPost } from '@public/apiv2/APITypes';
import { Event } from '@public/apiv2/Models';
import { APIError } from '@public/apiv2/reducers/trackerBaseApi';
import * as CurrencyUtils from '@public/util/currency';
import { sum } from '@public/util/reduce';

export const DonationErrors = {
  NO_AMOUNT: 'Donation amount is not set',

  AMOUNT_MINIMUM: (min: number, currency: string) =>
    `Donation amount is below the allowed minimum (${CurrencyUtils.asCurrency(min, { currency })})`,
  AMOUNT_MAXIMUM: (max: number, currency: string) =>
    `Donation amount is above the allowed maximum (${CurrencyUtils.asCurrency(max, { currency })})`,

  BID_SUM_EXCEEDS_TOTAL: 'Sum of bid amounts exceeds donation total.',

  INVALID_EMAIL: 'Email is not a valid email address',
};

export type DonationFormEntry = Omit<DonationPost, 'amount' | 'event'> & { amount?: number };

export default function validateDonation(event: Event, donation: DonationFormEntry, maximum: number): APIError | null {
  const sumOfBids = donation.bids.map(b => b.amount).reduce(sum, 0);
  const errors: Record<string, string> = {};

  if (donation.amount == null) {
    errors['amount'] = DonationErrors.NO_AMOUNT;
  } else if (donation.amount < event.minimumdonation) {
    errors['amount'] = DonationErrors.AMOUNT_MINIMUM(event.minimumdonation, event.paypalcurrency);
  } else if (donation.amount > maximum) {
    errors['amount'] = DonationErrors.AMOUNT_MAXIMUM(maximum, event.paypalcurrency);
  }

  if (donation.amount != null && sumOfBids > donation.amount) {
    errors['bids'] = DonationErrors.BID_SUM_EXCEEDS_TOTAL;
  }

  if (donation.requested_email !== '' && !validator.isEmail(donation.requested_email)) {
    errors['email'] = DonationErrors.INVALID_EMAIL;
  }

  return Object.keys(errors).length
    ? {
        status: 400,
        data: errors,
      }
    : null;
}
