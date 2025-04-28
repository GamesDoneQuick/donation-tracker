import { DateTime, Duration } from 'luxon';

export function toInputTime(s: string | DateTime): string {
  if (typeof s === 'string') {
    s = DateTime.fromISO(s);
  }
  if (!s.isValid) {
    throw new Error(`invalid time: ${s.invalidReason}`);
  }
  return s.toFormat("yyyy-LL-dd'T'T");
}

export function parseTime(s: string | DateTime): DateTime;
export function parseTime(s: null): null;
export function parseTime(s: string | DateTime | null): DateTime | null;

export function parseTime(s: string | DateTime | null): DateTime | null {
  if (typeof s !== 'string') {
    return s;
  }
  return DateTime.fromISO(s);
}

export const durationPattern = /^(((\d+):)?(([0-5]?\d):))?[0-5]?\d$/;

export function parseDuration(s: string | Duration): Duration;
export function parseDuration(s: null): null;
export function parseDuration(s: string | Duration | null): Duration | null;

export function parseDuration(s: string | Duration | null): Duration | null {
  if (typeof s !== 'string') {
    return s;
  }
  if (!durationPattern.test(s)) {
    throw new Error(`unparseable duration (string mismatch): ${s}`);
  }
  const parts = s.split(':');
  let value: Duration;
  switch (parts.length) {
    case 3:
      value = Duration.fromObject({ hour: +parts[0], minute: +parts[1], second: +parts[2] });
      break;
    case 2:
      value = Duration.fromObject({ minute: +parts[0], second: +parts[1] });
      break;
    case 1:
      value = Duration.fromObject({ second: +parts[0] });
      break;
    default:
      throw new Error(`unparseable duration (wrong number of parts): ${s}`);
  }
  if (!value.isValid) {
    throw new Error(`unparseable duration (invalid duration result): ${s}`);
  }
  return value;
}
