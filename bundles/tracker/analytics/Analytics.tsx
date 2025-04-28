import debounce from 'lodash/debounce';

import * as HTTPUtils from '@public/util/http';

import AnalyticsEvent from './AnalyticsEvent';

export { AnalyticsEvent };

interface AnalyticsEventData {
  event_name: string;
  properties: Record<string, unknown>;
}

let ANALYTICS_URL = '';
let EVENT_BUFFER: AnalyticsEventData[] = [];
const MAX_BUFFER_SIZE = 20;
const BUFFER_WAIT_TIME = 800;

export function setAnalyticsURL(newHost: string) {
  ANALYTICS_URL = newHost;
}

export function track(event: AnalyticsEvent, properties: Record<string, unknown>) {
  EVENT_BUFFER.push({ event_name: event, properties });

  if (EVENT_BUFFER.length >= MAX_BUFFER_SIZE) {
    flush.flush();
  } else {
    flush();
  }
}

const flush = debounce(
  () => {
    if (ANALYTICS_URL !== '') {
      HTTPUtils.post(ANALYTICS_URL, [...EVENT_BUFFER]);
    }

    EVENT_BUFFER = [];
  },
  BUFFER_WAIT_TIME,
  { maxWait: BUFFER_WAIT_TIME, trailing: true },
);
