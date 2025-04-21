import { BidChild, DonationPostBid, TreeBid } from '@public/apiv2/APITypes';
import { APIError } from '@public/apiv2/reducers/trackerBaseApi';
import * as CurrencyUtils from '@public/util/currency';
import { sum } from '@public/util/reduce';

import { DonationFormEntry } from '@tracker/donation/validateDonation';

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

  INVALID: 'Mismatched incentive. Please report this as a bug.',
  INVALID_PARENT: 'Parent is mismatched. Please report this as a bug.',
};

export default function validateBid(
  currency: string,
  newBid: DonationPostBid,
  incentive: TreeBid | null,
  donation: DonationFormEntry,
  option: BidChild | null,
): APIError | null {
  const preAllocatedTotal = donation.bids.map(b => b.amount).reduce(sum, 0);
  const remainingTotal = (donation.amount ?? 0) - preAllocatedTotal;

  const errors: Record<string, string> = {};

  if (newBid.amount < 1) {
    errors['amount'] = BidErrors.AMOUNT_MINIMUM(1, currency);
  }
  if (newBid.amount > remainingTotal) {
    errors['amount'] = BidErrors.AMOUNT_MAXIMUM(remainingTotal, currency);
  }

  if ('name' in newBid) {
    if (incentive?.id === newBid.parent && incentive.bid_type === 'choice') {
      if (newBid.name.length === 0) {
        errors['new_option'] = BidErrors.NO_CUSTOM_CHOICE;
      } else if (incentive.option_max_length != null && newBid.name.length > incentive.option_max_length) {
        errors['new_option'] = BidErrors.CUSTOM_CHOICE_LENGTH(incentive.option_max_length);
      }
    } else {
      // pathological
      errors['new_option'] = BidErrors.INVALID_PARENT;
    }
  } else if (
    option
      ? option.id !== newBid.id
      : incentive?.id !== newBid.id || (incentive?.id === newBid.id && incentive.bid_type !== 'challenge')
  ) {
    // pathological
    errors['generic'] = BidErrors.INVALID;
  }

  return Object.keys(errors).length > 0
    ? {
        status: 400,
        data: errors,
      }
    : null;
}
