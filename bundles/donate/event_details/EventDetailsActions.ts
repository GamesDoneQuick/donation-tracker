import { EventDetails } from './EventDetailsTypes';
import { ActionTypes } from '../Action';

// TODO: Refine `eventDetails` type with either:
// - a defined type for the pre-loaded props that have a different shape.
// - changing the API to match the existing `EventDetails` type.
export function loadEventDetails(eventDetails: any) {
  const {
    event: { receivername },
  } = eventDetails;

  return {
    type: ActionTypes.LOAD_EVENT_DETAILS,
    eventDetails: {
      receiverName: receivername,
      prizesUrl: eventDetails.prizesUrl,
      rulesUrl: eventDetails.rulesUrl,
      donateUrl: eventDetails.donateUrl,
      minimumDonation: eventDetails.minimumDonation,
      maximumDonation: eventDetails.maximumDonation,
      step: eventDetails.step,
    },
  };
}
