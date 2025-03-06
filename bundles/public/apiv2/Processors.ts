import { DateTime, Duration } from 'luxon';

import { APIInterstitial, APIPrize, APIRun } from '@public/apiv2/APITypes';
import { parseDuration, parseTime } from '@public/apiv2/helpers/luxon';
import { Prize, Run } from '@public/apiv2/Models';

export function processRun(r: APIRun, _0?: unknown, _1?: unknown, e?: number): Run {
  const { event, starttime, endtime, run_time, setup_time, anchor_time, ...rest } = r;
  const eventId = e || (typeof event === 'number' ? event : event?.id);
  if (eventId == null) {
    throw new Error('no event could be parsed');
  }
  return {
    event: eventId,
    starttime: starttime ? DateTime.fromISO(starttime) : null,
    endtime: endtime ? DateTime.fromISO(endtime) : null,
    run_time: parseDuration(run_time),
    setup_time: parseDuration(setup_time),
    anchor_time: anchor_time ? DateTime.fromISO(anchor_time) : null,
    ...rest,
  };
}

export function processPrize(p: APIPrize, _0?: unknown, _1?: unknown, e?: number): Prize {
  const { event, starttime, endtime, start_draw_time, end_draw_time, ...rest } = p;
  const eventId = e || (typeof event === 'number' ? event : event?.id);
  if (eventId == null) {
    throw new Error('no event could be parsed');
  }
  return {
    event: eventId,
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
>(m: AT, _i: number, _a: AT[], e?: number): T {
  const { event, length, ...rest } = m;
  const eventId = e || (typeof event === 'number' ? event : event?.id);
  if (eventId == null) {
    throw new Error('no event could be parsed');
  }
  return {
    ...rest,
    event: eventId,
    length: parseDuration(length),
  } as T;
}
