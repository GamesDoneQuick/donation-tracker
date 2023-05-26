import type { Event } from '../APITypes';
import Endpoints from '../Endpoints';
import HTTPUtils from '../HTTPUtils';

export async function getEvents() {
  const response = await HTTPUtils.get<Event[]>(Endpoints.EVENTS);
  return response.data;
}

interface GetEventParams {
  totals?: boolean;
}

export async function getEvent(eventId: string, queryParams?: GetEventParams) {
  const response = await HTTPUtils.get<Event>(Endpoints.EVENT(eventId), queryParams);
  return response.data;
}
