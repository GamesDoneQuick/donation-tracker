import type { Event } from '@gamesdonequick/donation-tracker-api-types';

import Endpoints from '../Endpoints';
import HTTPUtils from '../HTTPUtils';

interface GetEventParams {
  totals?: boolean;
}

export async function getEvent(eventId: number, queryParams?: GetEventParams) {
  const response = await HTTPUtils.get<Event>(Endpoints.EVENT(eventId), queryParams);
  return response.data;
}
