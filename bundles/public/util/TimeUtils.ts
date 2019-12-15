import { DateTime, DateTimeOptions, Duration, Interval } from 'luxon';

type TimestampFormat = 'ISO' | 'HTTP' | 'RFC2822' | 'SQL';

/* Parses the given `timestamp` into a DateTime. If no `format` is provided,
  the timestamp is parsed assuming the ISO format. For more details on what
  kinds of strings can be parsed by this method, see:
  https://moment.github.io/luxon/docs/manual/parsing.html

  This method is not intended to support parsing arbitrary time strings (e.g.,
  user input). */
function parseTimestamp(timestamp: string, format: TimestampFormat = 'ISO', options?: DateTimeOptions) {
  switch (format) {
    case 'ISO':
      return DateTime.fromISO(timestamp, options);
    case 'HTTP':
      return DateTime.fromHTTP(timestamp, options);
    case 'RFC2822':
      return DateTime.fromRFC2822(timestamp, options);
    case 'SQL':
      return DateTime.fromSQL(timestamp, options);
  }
}

/* Returns the current local time, according to the browser's timezone. */
function getNowLocal() {
  return DateTime.local();
}

/* Returns the current UTC time */
function getNowUTC() {
  return DateTime.utc();
}

function compare(source?: DateTime, other?: DateTime): number {
  const sourceMillis = source != null ? source.valueOf() : Infinity;
  const otherMillis = other != null ? other.valueOf() : Infinity;

  return sourceMillis - otherMillis;
}

export {
  // References to DateTime types should prefer using this export to avoid
  // creating implicit dependencies.
  DateTime,
  Duration,
  Interval,
};

export default {
  compare,
  getNowLocal,
  getNowUTC,
  parseTimestamp,
};
