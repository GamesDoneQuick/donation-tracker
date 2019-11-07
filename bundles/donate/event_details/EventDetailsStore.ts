import { StoreState } from '../Store';

const getEventDetailsState = (state: StoreState) => state.eventDetails;

export const getEventDetails = getEventDetailsState;
