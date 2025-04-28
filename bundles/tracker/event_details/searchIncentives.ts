import uniqBy from 'lodash/uniqBy';

import { Incentive } from './EventDetailsTypes';

export default function searchIncentives(incentives: Incentive[], query: string) {
  if (query === '') {
    return incentives;
  }

  const queryRegex = new RegExp(query, 'i');
  const matchingIncentives = incentives.filter(({ name, runname }) => {
    const haystack = `${name} ${runname}`;
    return haystack.match(queryRegex);
  });

  return uniqBy(matchingIncentives, incentive => `${incentive.runname}--${incentive.name}`);
}
