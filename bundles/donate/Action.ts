import keyMirror from 'keymirror';

import { DonationAction } from './donation/DonationTypes';
import { EventDetailsAction } from './event_details/EventDetailsTypes';

export type Action = DonationAction | EventDetailsAction;

export const ActionTypes = keyMirror({
  // Donations
  LOAD_DONATION: null,
  CREATE_BID: null,
  DELETE_BID: null,
  UPDATE_DONATION: null,

  // Event Details
  LOAD_EVENT_DETAILS: null,
  LOAD_INCENTIVES: null,
});

export type ActionFor<T extends keyof typeof ActionTypes> = Extract<
  Action,
  {
    type: T;
  }
>;
