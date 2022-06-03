import type { Event } from '../APITypes';
import Endpoints from '../Endpoints';
import HTTPUtils from '../HTTPUtils';

export async function getEvents() {
  const response = await HTTPUtils.get<Event[]>(Endpoints.EVENTS);
  return response.data;
}

export async function getEvent(eventId: string) {
  const response = await HTTPUtils.get<Event>(Endpoints.EVENT(eventId));
  return response.data;
}
