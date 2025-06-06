import keyBy from 'lodash/keyBy';

import { ActionFor, ActionTypes } from '@tracker/Action';

import { EventDetails, EventDetailsAction } from './EventDetailsTypes';

type EventDetailsState = EventDetails;

const initialState: EventDetailsState = {
  currency: 'USD', // Default to USD to make tests happy
  receiverName: '',
  receiverSolicitationText: '',
  receiverLogo: '',
  receiverPrivacyPolicy: '',
  prizesUrl: '',
  donateUrl: '',
  minimumDonation: 1,
  maximumDonation: Infinity,
  step: 0.01,
  availableIncentives: {},
  prizes: [],
};

function handleLoadEventDetails(state: EventDetailsState, action: ActionFor<'LOAD_EVENT_DETAILS'>) {
  const { eventDetails } = action;

  return {
    ...eventDetails,
    availableIncentives: {
      ...eventDetails.availableIncentives,
    },
    prizes: [...eventDetails.prizes],
  };
}

function handleLoadIncentives(state: EventDetailsState, action: ActionFor<'LOAD_INCENTIVES'>) {
  const { incentives } = action;

  return {
    ...state,
    availableIncentives: keyBy(incentives, 'id'),
  };
}

export default function reducer(state = initialState, action: EventDetailsAction) {
  switch (action.type) {
    case ActionTypes.LOAD_EVENT_DETAILS:
      return handleLoadEventDetails(state, action);
    case ActionTypes.LOAD_INCENTIVES:
      return handleLoadIncentives(state, action);
    default:
      return state;
  }
}
