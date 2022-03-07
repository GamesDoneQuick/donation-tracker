import { ActionTypes } from '@tracker/Action';

import { EventDetails, Incentive } from './EventDetailsTypes';

export function loadEventDetails(eventDetails: EventDetails) {
  return {
    type: ActionTypes.LOAD_EVENT_DETAILS,
    eventDetails,
  };
}

export function loadIncentives(incentives: Incentive[]) {
  return {
    type: ActionTypes.LOAD_INCENTIVES,
    incentives,
  };
}
