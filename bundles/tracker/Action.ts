import keyMirror from 'keymirror';

import { DonationAction } from './donation/DonationTypes';
import { EventDetailsAction } from './event_details/EventDetailsTypes';
import { EventAction } from './events/EventTypes';
import { PrizeAction } from './prizes/PrizeTypes';

export type Action = DonationAction | EventAction | EventDetailsAction | PrizeAction;

export const ActionTypes = keyMirror({
  // Donations
  LOAD_DONATION: null,
  CREATE_BID: null,
  DELETE_BID: null,
  UPDATE_DONATION: null,

  // Event Details
  LOAD_EVENT_DETAILS: null,
  LOAD_INCENTIVES: null,

  // Events
  FETCH_EVENTS_STARTED: null,
  FETCH_EVENTS_SUCCESS: null,
  FETCH_EVENTS_FAILED: null,
  SELECT_EVENT: null,

  // Prizes
  FETCH_PRIZES_STARTED: null,
  FETCH_PRIZES_SUCCESS: null,
  FETCH_PRIZES_FAILED: null,
});

export type ActionFor<T extends keyof typeof ActionTypes> = Extract<
  Action,
  {
    type: T;
  }
>;
