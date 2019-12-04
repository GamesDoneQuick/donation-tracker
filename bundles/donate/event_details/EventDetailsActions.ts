import { EventDetails } from './EventDetailsTypes';
import { ActionTypes } from '../Action';

export function loadEventDetails(eventDetails: EventDetails) {
  return {
    type: ActionTypes.LOAD_EVENT_DETAILS,
    eventDetails,
  };
}
