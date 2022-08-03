import _ from 'lodash';

import { ActionFor, ActionTypes } from '@tracker/Action';

import { Event, EventAction } from './EventTypes';

type EventsState = {
  events: { [id: string]: Event };
  selectedEventId?: number;
  loading: boolean;
};

const initialState: EventsState = {
  events: {},
  selectedEventId: undefined,
  loading: false,
};

function handleFetchEventsStarted(state: EventsState, action: ActionFor<'FETCH_EVENTS_STARTED'>) {
  return {
    ...state,
    loading: true,
  };
}

function handleFetchEventsSuccess(state: EventsState, action: ActionFor<'FETCH_EVENTS_SUCCESS'>) {
  const { events } = action;

  return {
    ...state,
    events: {
      ...state.events,
      ..._.keyBy(events, 'id'),
    },
    loading: false,
  };
}

function handleFetchEventsFailed(state: EventsState, action: ActionFor<'FETCH_EVENTS_FAILED'>) {
  return {
    ...state,
    loading: false,
  };
}

function handleSelectEvent(state: EventsState, action: ActionFor<'SELECT_EVENT'>) {
  const { eventId } = action;

  return {
    ...state,
    selectedEventId: eventId,
  };
}

export default function reducer(state = initialState, action: EventAction) {
  switch (action.type) {
    case ActionTypes.FETCH_EVENTS_STARTED:
      return handleFetchEventsStarted(state, action);
    case ActionTypes.FETCH_EVENTS_SUCCESS:
      return handleFetchEventsSuccess(state, action);
    case ActionTypes.FETCH_EVENTS_FAILED:
      return handleFetchEventsFailed(state, action);
    case ActionTypes.SELECT_EVENT:
      return handleSelectEvent(state, action);
    default:
      return state;
  }
}
