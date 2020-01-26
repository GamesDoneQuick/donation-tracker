import { EventDetails, Incentive } from './EventDetailsTypes';
import { ActionTypes } from '../Action';

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
