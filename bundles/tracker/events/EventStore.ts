import { createSelector } from 'reselect';
import createCachedSelector from 're-reselect';

import { StoreState } from '../Store';

const getEventsState = (state: StoreState) => state.events;
const getEventId = (state: StoreState, { eventId }: { eventId: string }) => {
  const events = state.events && state.events.events;
  let event;
  if (/\D/.test(eventId)) {
    event = Object.values(events).find(event => event.short === eventId);
  }
  return event ? event.id : eventId;
};
export const getSelectedEventId = (state: StoreState) => state.events.selectedEventId;

export const getSelectedEvent = createSelector([getEventsState, getSelectedEventId], (state, eventId) =>
  eventId != null ? state.events[eventId] : undefined,
);

export const getEvents = createSelector([getEventsState], state => Object.values(state.events));

export const getEvent = createCachedSelector([getEventsState, getEventId], (state, eventId) =>
  eventId != null ? state.events[eventId] : undefined,
)(getEventId);
