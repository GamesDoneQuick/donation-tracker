import _ from 'lodash';

import * as CurrencyUtils from '../../public/util/currency';
import { Incentive } from '../event_details/EventDetailsTypes';
import { Bid, Donation, Validation } from './DonationTypes';

const BID_MINIMUM_AMOUNT = 1.0;

export default function validateBid(
  newBid: Partial<Bid>,
  incentive: Incentive,
  donation: Donation,
  bids: Array<Bid>,
  hasChildIncentives: boolean,
  hasChildSelected: boolean,
  isCustom: boolean = false,
): Validation {
  const preAllocatedTotal = _.sumBy(bids, 'amount');
  const remainingTotal = donation.amount ? donation.amount - preAllocatedTotal : 0;

  const errors = [];

  if (newBid.incentiveId == null) {
    errors.push({ field: 'incentiveId', message: 'Bid must go towards an incentive' });
  } else if (hasChildIncentives && !hasChildSelected && !isCustom) {
    errors.push({ field: 'incentiveId', message: 'Bid must select a choice' });
  }

  if (newBid.amount == null) {
    errors.push({ field: 'amount', message: 'Bid amount is required' });
  } else {
    if (newBid.amount < BID_MINIMUM_AMOUNT) {
      errors.push({
        field: 'amount',
        message: `Bid amount must be greater than (${CurrencyUtils.asCurrency(BID_MINIMUM_AMOUNT)})`,
      });
    }

    if (newBid.amount > remainingTotal) {
      errors.push({
        field: 'amount',
        message: `Amount is larger than remaining total (${CurrencyUtils.asCurrency(remainingTotal)}).`,
      });
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
