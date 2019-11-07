import { EventDetails } from './EventDetailsTypes';
import { ActionTypes } from '../Action';

// TODO: Refine `eventDetails` type with either:
// - a defined type for the pre-loaded props that have a different shape.
// - changing the API to match the existing `EventDetails` type.
export function loadEventDetails(eventDetails: EventDetails) {
  return {
    type: ActionTypes.LOAD_EVENT_DETAILS,
    eventDetails,
  };
}
