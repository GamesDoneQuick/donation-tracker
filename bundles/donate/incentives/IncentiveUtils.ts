import _ from 'lodash';

import { Incentive } from './IncentiveTypes';

export function validateBid({ amount, total, selected, choice, newChoice }: any) {
  if (amount <= 0) {
    return [false, 'Amount must be greater than 0.'];
  }

  if (amount > total) {
    return [false, `Amount cannot be greater than $${total}.`];
  }

  if (!selected || selected.goal) {
    return [true, null];
  }

  return [true, null];
}

export function searchIncentives(incentives: Array<Incentive>, query: string) {
  if (query === '') {
    return incentives;
  }

  const queryRegex = new RegExp(query, 'i');
  const matchingIncentives = incentives.filter(({ name, runname }) => {
    const haystack = `${name} ${runname}`;
    return haystack.match(queryRegex);
  });

  return _.uniqBy(matchingIncentives, incentive => `${incentive.runname}--${incentive.name}`);
}
