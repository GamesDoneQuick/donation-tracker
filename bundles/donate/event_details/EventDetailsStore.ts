import { createSelector } from 'reselect';

import { StoreState } from '../Store';
import { Incentive } from './EventDetailsTypes';

const getEventDetailsState = (state: StoreState) => state.eventDetails;
export const getIncentivesById = (state: StoreState) => state.eventDetails.availableIncentives;
export const getPrizes = (state: StoreState) => state.eventDetails.prizes;

export const getEventDetails = getEventDetailsState;

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
