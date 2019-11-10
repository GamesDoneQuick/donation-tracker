import _ from 'lodash';

import { Incentive } from '../event_details/EventDetailsTypes';
import { Bid, Donation, Validation } from './DonationTypes';

export default function validateBid(
  newBid: Partial<Bid>,
  incentive: Incentive,
  donation: Donation,
  bids: Array<Bid>,
  isCustom: boolean = false,
): Validation {
  const preAllocatedTotal = _.sumBy(bids, 'amount');
  const remainingTotal = donation.amount ? donation.amount - preAllocatedTotal : 0;

  const errors = [];

  if (newBid.incentiveId == null) {
    errors.push({ field: 'incentiveId', message: 'Bid must go towards an incentive' });
  }

  if (newBid.amount == null) {
    errors.push({ field: 'amount', message: 'Bid amount is required' });
  } else {
    if (newBid.amount <= 0) {
      errors.push({ field: 'amount', message: 'Bid amount must be greater than 0.' });
    }

    if (newBid.amount > remainingTotal) {
      errors.push({ field: 'amount', message: `Amount is larger than remaining total ($${remainingTotal}).` });
    }
  }

  if (isCustom) {
    if (newBid.customoptionname == null || newBid.customoptionname.length === 0) {
      errors.push({ field: 'new option', message: 'Must provide a new option' });
    } else if (incentive.maxlength != null && newBid.customoptionname.length > incentive.maxlength) {
      errors.push({ field: 'new option', message: `Must be less than ${incentive.maxlength} characters` });
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}
