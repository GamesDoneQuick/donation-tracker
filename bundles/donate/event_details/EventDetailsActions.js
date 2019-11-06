import { EventDetails } from './EventDetailsTypes';
import { ActionTypes } from '../Action';

export function loadEventDetails(eventDetails) {
  // `event` doesn't have any other useful props for this page, so receivername
  // is pulled out and flattened into the details structure for the reducer.
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
