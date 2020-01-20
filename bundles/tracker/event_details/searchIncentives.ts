import _ from 'lodash';

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

  return _.uniqBy(matchingIncentives, incentive => `${incentive.runname}--${incentive.name}`);
}
