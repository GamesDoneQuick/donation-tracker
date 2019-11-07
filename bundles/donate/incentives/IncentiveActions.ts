import { Incentive } from './IncentiveTypes';
import { ActionTypes } from '../Action';

function parseCurrency(amount: any) {
  const parsed = parseFloat(amount);
  return parsed === NaN ? undefined : parsed;
}

export function loadIncentives(incentives: Array<Incentive>) {
  // Convert Django's serialization of amounts/goals to floats
  const transformedIncentives = incentives.map(incentive => {
    return {
      ...incentive,
      amount: parseCurrency(incentive.amount) || 0.0,
      goal: parseCurrency(incentive.goal),
    };
  });

  return {
    type: ActionTypes.LOAD_INCENTIVES,
    incentives: transformedIncentives,
  };
}

export function createBid(bid: { incentiveId: number; customOption: string; amount: number }) {
  return {
    type: ActionTypes.CREATE_BID,
    bid: {
      ...bid,
      customOption: bid.customOption === '' ? undefined : bid.customOption,
    },
  };
}

export function deleteBid(incentiveId: number) {
  return {
    type: ActionTypes.DELETE_BID,
    incentiveId,
  };
}
