import * as HTTPUtils from '../../public/util/http';
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

let flushTimeoutId: number | undefined;

export function setAnalyticsURL(newHost: string) {
  ANALYTICS_URL = newHost;
}

export function track(event: AnalyticsEvent, properties: Record<string, unknown>) {
  // We don't want to be sending dozens of tracking requests every time
  // a single thing happens. This queues events to try and group them
  // into manageable batches while still guaranteeing that events are
  // emitted within a reasonable amount of time.

  clearTimeout(flushTimeoutId);
  EVENT_BUFFER.push({ event_name: event, properties });
  flushTimeoutId = undefined;

  if (EVENT_BUFFER.length >= MAX_BUFFER_SIZE) {
    flush();
  } else {
    // Node types conflict here and returns a Timeout instead of a number.
    // Casting to Function uses the DOM definition instead.
    // TODO: Remove Node types from resolution here.
    // eslint-disable-next-line @typescript-eslint/ban-types
    flushTimeoutId = setTimeout(flush as Function, BUFFER_WAIT_TIME);
  }
}

export function flush() {
  if (ANALYTICS_URL !== '') {
    HTTPUtils.post(ANALYTICS_URL, [...EVENT_BUFFER]);
  }

  EVENT_BUFFER = [];
}
