import { createSelector } from 'reselect';
import _ from 'lodash';

import { StoreState } from '../Store';
import { Incentive } from './IncentiveTypes';

export const getIncentivesById = (state: StoreState) => state.incentives.incentives;
export const getBidsById = (state: StoreState) => state.incentives.bids;

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
  [getIncentivesById, (_: StoreState, incentiveId: number) => incentiveId],
  (incentivesById, incentiveId) => incentivesById[incentiveId],
);

export const getTopLevelIncentives = createSelector(
  [getIncentives],
  incentives => incentives.filter(incentive => !incentive.parent),
);

export const getChildIncentives = createSelector(
  [getIncentives, (_: StoreState, incentiveId: number) => incentiveId],
  (incentives, parentId): Array<Incentive> => {
    if (parentId == null) return [];
    return incentives.filter(incentive => incentive.parent && incentive.parent.id === parentId);
  },
);
