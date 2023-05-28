import _ from 'lodash';

import * as CurrencyUtils from '@public/util/currency';

import { Incentive } from '@tracker/event_details/EventDetailsTypes';

import { BID_MINIMUM_AMOUNT } from './DonationConstants';
import { Bid, Donation, Validation } from './DonationTypes';

export const BidErrors = {
  NO_INCENTIVE: 'Bid must go towards an incentive',
  NO_CHOICE: 'Bid must select a choice',
  NO_AMOUNT: 'Bid amount is required',

  AMOUNT_MINIMUM: (min: number, currency: string) =>
    `Bid amount must be greater than (${CurrencyUtils.asCurrency(min, { currency })})`,
  AMOUNT_MAXIMUM: (max: number, currency: string) =>
    `Amount is larger than remaining total (${CurrencyUtils.asCurrency(max, { currency })}).`,

  NO_CUSTOM_CHOICE: 'New option does not have a value',
  CUSTOM_CHOICE_LENGTH: (maxLength: number) => `New choice must be less than ${maxLength} characters`,
};

export default function validateBid(
  currency: string,
  newBid: Partial<Bid>,
  incentive: Incentive,
  donation: Donation,
  bids: Bid[],
  hasChildIncentives: boolean,
  hasChildSelected: boolean,
  isCustom = false,
): Validation {
  const preAllocatedTotal = _.sumBy(
    bids.filter(bid => bid.incentiveId),
    'amount',
  );
  const remainingTotal = donation.amount ? donation.amount - preAllocatedTotal : 0;

  const errors = [];

  if (newBid.incentiveId == null) {
    errors.push({ field: 'incentiveId', message: BidErrors.NO_INCENTIVE });
  } else if (hasChildIncentives && !hasChildSelected && !isCustom && !incentive.chain) {
    errors.push({ field: 'incentiveId', message: BidErrors.NO_CHOICE });
  }

  if (newBid.amount == null) {
    errors.push({ field: 'amount', message: BidErrors.NO_AMOUNT });
  } else {
    if (newBid.amount < BID_MINIMUM_AMOUNT) {
      errors.push({
        field: 'amount',
        message: BidErrors.AMOUNT_MINIMUM(BID_MINIMUM_AMOUNT, currency),
      });
    }

    if (newBid.amount > remainingTotal) {
      errors.push({
        field: 'amount',
        message: BidErrors.AMOUNT_MAXIMUM(remainingTotal, currency),
      });
    }
  }

  if (isCustom) {
    if (newBid.customoptionname == null || newBid.customoptionname.length === 0) {
      errors.push({ field: 'new option', message: BidErrors.NO_CUSTOM_CHOICE });
    } else if (incentive.maxlength != null && newBid.customoptionname.length > incentive.maxlength) {
      errors.push({ field: 'new option', message: BidErrors.CUSTOM_CHOICE_LENGTH(incentive.maxlength) });
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}
