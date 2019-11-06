import { createSelector } from 'reselect';
import _ from 'lodash';

export const getIncentivesById = state => state.incentives.incentives;
export const getBidsById = state => state.incentives.bids;

export const getBids = createSelector(
  [getBidsById],
  bidsById => Object.values(bidsById),
);

export const getAllocatedBidTotal = createSelector(
  [getBids],
  bids => _.sumBy(bids, 'amount'),
);

export const getIncentives = createSelector(
  [getIncentivesById],
  incentivesById => Object.values(incentivesById),
);

export const getIncentive = createSelector(
  [getIncentivesById, (_, incentiveId) => incentiveId],
  (incentivesById, incentiveId) => incentivesById[incentiveId],
);

export const getTopLevelIncentives = createSelector(
  [getIncentives],
  incentives => incentives.filter(incentive => !incentive.parent),
);

export const getChildIncentives = createSelector(
  [getIncentives, (_, incentiveId) => incentiveId],
  (incentives, parentId) => {
    if (parentId == null) return [];
    return incentives.filter(incentive => incentive.parent && incentive.parent.id === parentId);
  },
);
