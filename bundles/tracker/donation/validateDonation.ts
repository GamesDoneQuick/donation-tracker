import _ from 'lodash';
import validator from 'validator';

import * as CurrencyUtils from '@public/util/currency';

import { EventDetails } from '@tracker//event_details/EventDetailsTypes';

import { MAX_BIDS_PER_DONATION } from './DonationConstants';
import { Bid, Donation, Validation } from './DonationTypes';

export const DonationErrors = {
  NO_AMOUNT: '寄付額が設定されていません',

  AMOUNT_MINIMUM: (min: number) => `寄付額は最低金額の (${CurrencyUtils.asCurrency(min)}) 以上に設定してください`,
  AMOUNT_MAXIMUM: (max: number) => `寄付額は最高金額の (${CurrencyUtils.asCurrency(max)}) 以下に設定してください`,

  TOO_MANY_BIDS: (maxBids: number) => `1回の寄付に設定できるビッツは ${maxBids} 件までです`,
  BID_SUM_EXCEEDS_TOTAL: 'ビッツ額の合計が寄付額を越えています。',

  INVALID_EMAIL: '無効なメールアドレスです',
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
