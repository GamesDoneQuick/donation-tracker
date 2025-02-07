import { DateTime, Duration } from 'luxon';

import { parseDuration, parseTime } from '@public/apiv2/helpers/luxon';

describe('luxon helpers', () => {
  describe('parseTime', () => {
    it('can parse valid ISO times', () => {
      const s = '2024-01-01T12:00Z';
      const d = DateTime.fromISO(s);
      expect(d.isValid).toBeTrue();
      expect(parseTime(s).equals(d)).toBeTrue();
      expect(parseTime(d)).toBe(d);
      expect(parseTime(null)).toBeNull();
    });
  });

  describe('parseDuration', () => {
    it('can parse valid-ish durations', () => {
      expect(parseDuration('5').equals(Duration.fromObject({ seconds: 5 }))).toBeTrue();
      expect(parseDuration('5:5').equals(Duration.fromObject({ minutes: 5, seconds: 5 }))).toBeTrue();
      expect(parseDuration('5:5:5').equals(Duration.fromObject({ hours: 5, minutes: 5, seconds: 5 }))).toBeTrue();
      expect(
        parseDuration('999:59:59').equals(Duration.fromObject({ hours: 999, minutes: 59, seconds: 59 })),
      ).toBeTrue();
      expect(parseDuration('0:0:0').equals(Duration.fromMillis(0))).toBeTrue();
      expect(parseDuration(null)).toBeNull();
      const d = Duration.fromMillis(1000);
      expect(parseDuration(d)).toBe(d);
    });

    it('throws on invalid input', () => {
      expect(() => {
        parseDuration('');
      }).toThrow();
      expect(() => {
        parseDuration('foo');
      }).toThrow();
      expect(() => {
        parseDuration('60');
      }).toThrow();
      expect(() => {
        parseDuration('1:1:1:1');
      }).toThrow();
      // TODO? right now it just returns the invalid duration right back
      // expect(() => parseDuration(Duration.invalid('test'))).toThrow();
    });
  });
});
