import keyMirror from 'keymirror';

import { DonationAction } from './donation/DonationTypes';
import { EventDetailsAction } from './event_details/EventDetailsTypes';
import { IncentivesAction } from './incentives/IncentiveTypes';

export type Action = DonationAction | IncentivesAction | EventDetailsAction;

export const ActionTypes = keyMirror({
  // Donations
  LOAD_DONATION: null,
  UPDATE_DONATION: null,

  // Incentives
  LOAD_INCENTIVES: null,
  CREATE_BID: null,
  DELETE_BID: null,

  // Event Details
  LOAD_EVENT_DETAILS: null,
});

export type ActionFor<T extends keyof typeof ActionTypes> = Extract<
  Action,
  {
    type: T;
  }
>;
