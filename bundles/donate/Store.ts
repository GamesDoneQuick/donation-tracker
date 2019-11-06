import { createStore, applyMiddleware, combineReducers } from 'redux';
import thunk from 'redux-thunk';

import { Action } from './Action';
import DonationReducer from './donation/DonationReducer';
import EventDetailsReducer from './event_details/EventDetailsReducer';
import IncentivesReducer from './incentives/IncentivesReducer';

const combinedReducer = combineReducers({
  incentives: IncentivesReducer,
  eventDetails: EventDetailsReducer,
  donation: DonationReducer,
});

export type StoreState = ReturnType<typeof combinedReducer>;

export const store = createStore(combinedReducer, applyMiddleware(thunk));
