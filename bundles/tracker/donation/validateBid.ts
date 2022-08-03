import _ from 'lodash';

import * as CurrencyUtils from '@public/util/currency';

import { Incentive } from '@tracker/event_details/EventDetailsTypes';

import { BID_MINIMUM_AMOUNT } from './DonationConstants';
import { Bid, Donation, Validation } from './DonationTypes';

export const BidErrors = {
  NO_INCENTIVE: '投票はインセンティブに割り当ててください。',
  NO_CHOICE: '投票では選択肢を選んでください。',
  NO_AMOUNT: '投票金額を入力してください。',

  AMOUNT_MINIMUM: (min: number) => `金額は(${CurrencyUtils.asCurrency(min)})以上にしてください。`,
  AMOUNT_MAXIMUM: (max: number) => `金額が残りの(${CurrencyUtils.asCurrency(max)})を越えています。`,

  NO_CUSTOM_CHOICE: '選択肢の内容を入力してください。',
  CUSTOM_CHOICE_LENGTH: (maxLength: number) => `新しい選択肢は ${maxLength} 文字以下にしてください。`,
};

export default function validateBid(
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
  } else if (hasChildIncentives && !hasChildSelected && !isCustom) {
    errors.push({ field: 'incentiveId', message: BidErrors.NO_CHOICE });
  }

  if (newBid.amount == null) {
    errors.push({ field: 'amount', message: BidErrors.NO_AMOUNT });
  } else {
    if (newBid.amount < BID_MINIMUM_AMOUNT) {
      errors.push({
        field: 'amount',
        message: BidErrors.AMOUNT_MINIMUM(BID_MINIMUM_AMOUNT),
      });
    }

    if (newBid.amount > remainingTotal) {
      errors.push({
        field: 'amount',
        message: BidErrors.AMOUNT_MAXIMUM(remainingTotal),
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
