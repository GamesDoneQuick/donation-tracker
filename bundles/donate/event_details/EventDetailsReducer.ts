import _ from 'lodash';

import { ActionFor, ActionTypes } from '../Action';
import { EventDetails, EventDetailsAction } from './EventDetailsTypes';

type EventDetailsState = EventDetails;

const initialState = {
  receiverName: '',
  prizesUrl: '',
  rulesUrl: '',
  donateUrl: '',
  minimumDonation: 1,
  maximumDonation: Infinity,
  step: 0.01,
};

function handleLoadEventDetails(state: EventDetailsState, action: ActionFor<'LOAD_EVENT_DETAILS'>) {
  const { eventDetails } = action;
  return _.merge(
    { ...initialState },
    {
      receiverName: eventDetails.receiverName,
      prizesUrl: eventDetails.prizesUrl,
      rulesUrl: eventDetails.rulesUrl,
      donateUrl: eventDetails.donateUrl,
      minimumDonation: eventDetails.minimumDonation,
      maximumDonation: eventDetails.maximumDonation,
      step: eventDetails.step,
    },
  );
}

export default function reducer(state = initialState, action: EventDetailsAction) {
  switch (action.type) {
    case ActionTypes.LOAD_EVENT_DETAILS:
      return handleLoadEventDetails(state, action);
    default:
      return state;
  }
}
