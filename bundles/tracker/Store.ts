import { applyMiddleware, combineReducers, createStore } from 'redux';
import thunk from 'redux-thunk';
import { composeWithDevTools } from '@redux-devtools/extension';

import DonationReducer from './donation/DonationReducer';
import EventDetailsReducer from './event_details/EventDetailsReducer';
import EventReducer from './events/EventReducer';
import PrizeReducer from './prizes/PrizeReducer';

export const combinedReducer = combineReducers({
  eventDetails: EventDetailsReducer,
  donation: DonationReducer,
  events: EventReducer,
  prizes: PrizeReducer,
});

export type StoreState = ReturnType<typeof combinedReducer>;

const composeEnhancers = composeWithDevTools({
  // Uncomment to see stacktraces in the devtools for each action fired.
  // trace: true,
});

export function createTrackerStore() {
  return createStore(combinedReducer, composeEnhancers(applyMiddleware(thunk)));
}
