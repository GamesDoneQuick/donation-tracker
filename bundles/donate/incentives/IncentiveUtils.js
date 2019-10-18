import _ from 'lodash';

export function validateBid({amount, total, selected, choice, newChoice}) {
  if (amount <= 0) {
    return [false, 'Amount must be greater than 0.'];
  }

  if (amount > total) {
    return [false, `Amount cannot be greater than $${total}.`];
  }

  if (!selected || selected.goal) {
    return [true, null];
  }

  if (newChoice && !newOptionValue) {
    return [false, 'Must enter new option.'];
  }

  if (!newOption && !selectedChoice) {
    return [false, 'Must pick an option.'];
  }

  return [true, null];
}

export function searchIncentives(query, incentives) {
  if (query === "") {
    return incentives;
  }

  const queryRegex = new RegExp(query, 'i');
  const matchingIncentives = incentives.filter(({name, runname}) => {
    const haystack = `${name} ${runname}`;
    return haystack.match(queryRegex);
  });

  return _.uniqBy(matchingIncentives, incentive => `${incentive.runname}--${incentive.name}`);
}
