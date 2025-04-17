import { DateTime, Duration } from 'luxon';

import { APIDonation, APIEvent, APIInterstitial, APIMilestone, APIPrize, APIRun } from '@public/apiv2/APITypes';
import { parseDuration, parseTime } from '@public/apiv2/helpers/luxon';
import { Donation, Event, Milestone, Prize, Run } from '@public/apiv2/Models';

export function processEvent(e: APIEvent): Event {
  const { datetime, ...rest } = e;
  return {
    datetime: DateTime.fromISO(datetime),
    ...rest,
  };
}

/*
 * either the event is from the API model itself, or from the event filter parameter from the original arguments
 */

function parseEvent(e: number | undefined, event: APIEvent | number | undefined) {
  const eventId = e || (typeof event === 'number' ? event : event?.id);
  if (eventId == null) {
    throw new Error('no event could be parsed');
  }
  return eventId;
}

export function processRun(r: APIRun, _i?: number, _a?: APIRun[], e?: number): Run {
  const { event, starttime, endtime, run_time, setup_time, anchor_time, ...rest } = r;
  return {
    event: parseEvent(e, event),
    starttime: starttime ? DateTime.fromISO(starttime) : null,
    endtime: endtime ? DateTime.fromISO(endtime) : null,
    run_time: parseDuration(run_time),
    setup_time: parseDuration(setup_time),
    anchor_time: anchor_time ? DateTime.fromISO(anchor_time) : null,
    ...rest,
  };
}

export function processPrize(p: APIPrize, _i?: number, _a?: APIPrize[], e?: number): Prize {
  const { event, starttime, endtime, start_draw_time, end_draw_time, ...rest } = p;
  return {
    event: parseEvent(e, event),
    starttime: parseTime(starttime),
    endtime: parseTime(endtime),
    start_draw_time: parseTime(start_draw_time),
    end_draw_time: parseTime(end_draw_time),
    ...rest,
  };
}

export function processInterstitial<
  AT extends APIInterstitial,
  T extends Omit<AT, 'event' | 'length'> & { event: number; length: Duration },
>(m: AT, _i?: number, _a?: AT[], e?: number): T {
  const { event, length, ...rest } = m;
  return {
    ...rest,
    event: parseEvent(e, event),
    length: parseDuration(length),
  } as T;
}

export function processMilestone(m: APIMilestone, _i?: number, _a?: APIMilestone[], e?: number): Milestone {
  const { event, ...rest } = m;
  return {
    event: parseEvent(e, event),
    ...rest,
  };
}

export function processDonation(
  d: APIDonation,
  _i?: number,
  _a?: APIDonation[],
  { eventId: e }: { eventId?: number } = {},
): Donation {
  const { event, timereceived, ...rest } = d;
  return {
    event: parseEvent(e, event),
    timereceived: parseTime(timereceived),
    ...rest,
  };
}
