function parseCurrency(amount) {
  const parsed = parseFloat(amount);
  return parsed === NaN ? null : parsed;
}

export function loadIncentives(incentives) {
  // Convert Django's serialization of amounts/goals to floats
  const transformedIncentives = incentives.map(incentive => {
    return {
      ...incentive,
      amount: parseCurrency(incentive.amount),
      goal: parseCurrency(incentive.goal),
    };
  });

  return {
    type: 'incentives/LOAD_INCENTIVES',
    data: {
      incentives: transformedIncentives,
    },
  };
}

export function createBid({ incentiveId, customOption, amount }) {
  return {
    type: 'incentives/CREATE_BID',
    data: {
      bid: {
        incentiveId,
        customOption: customOption === '' ? null : customOption,
        amount,
      },
    },
  };
}

export function deleteBid(incentiveId) {
  return {
    type: 'donate/DELETE_BID',
    data: {
      incentiveId,
    },
  };
}
