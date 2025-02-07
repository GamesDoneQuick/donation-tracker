import type { APIEvent } from '../APITypes';
import Endpoints from '../Endpoints';
import HTTPUtils from '../HTTPUtils';

interface GetEventParams {
  totals?: boolean;
}

export async function getEvent(eventId: number, queryParams?: GetEventParams) {
  const response = await HTTPUtils.get<APIEvent>(Endpoints.EVENT(eventId), queryParams);
  return response.data;
}
