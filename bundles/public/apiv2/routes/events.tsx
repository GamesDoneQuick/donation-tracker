import type { APIEvent, PaginationInfo } from '../APITypes';
import Endpoints from '../Endpoints';
import HTTPUtils from '../HTTPUtils';

interface GetEventParams {
  totals?: boolean;
}

export async function getEvents(queryParams?: GetEventParams) {
  const response = await HTTPUtils.get<PaginationInfo<APIEvent>>(Endpoints.EVENTS, queryParams);
  return response.data;
}

export async function getEvent(eventId: string, queryParams?: GetEventParams) {
  const response = await HTTPUtils.get<APIEvent>(Endpoints.EVENT(eventId), queryParams);
  return response.data;
}
