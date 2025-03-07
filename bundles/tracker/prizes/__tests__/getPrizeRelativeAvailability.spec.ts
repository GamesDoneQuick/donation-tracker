import { DateTime } from 'luxon';

import { OrderedRun, Prize } from '@public/apiv2/Models';
import { processPrize, processRun } from '@public/apiv2/Processors';
import TimeUtils from '@public/util/TimeUtils';

import { getFixturePrize } from '@spec/fixtures/Prize';
import { getFixtureRun } from '@spec/fixtures/run';
import { getFixtureTalent } from '@spec/fixtures/talent';

import getPrizeRelativeAvailability, {
  ALLOWED_ESTIMATED_TIMES,
  EXACT_TIME_RELATIVE_LIMIT,
} from '../getPrizeRelativeAvailability';

const now = TimeUtils.parseTimestamp('2019-12-10T10:00:00Z');

const run1: OrderedRun = processRun(
  getFixtureRun({
    name: 'Spyro the Dragon',
    display_name: 'Spyro the Dragon',
    twitch_name: 'Spyro the Dragon',
    runners: [getFixtureTalent({ name: 'faulty' })],
    console: 'PS1',
    commentators: [],
    description: 'Spyro a drago',
    starttime: '2019-12-10T09:00:00Z',
    endtime: '2019-12-10T11:00:00Z',
    order: 5,
    run_time: '1:40:00',
    setup_time: '0:05:00',
    category: '120%',
    release_year: 1997,
    tech_notes: '',
  }),
) as OrderedRun;

console.assert(run1.order != null);

const defaultPrize = processPrize(
  getFixturePrize({
    id: 2,
    name: 'Some game codes with a long name',
    image: '/media/image.png',
    altimage: '/media/altimage.png',
    imagefile: '/media/imagefile.png',
    description: 'This prize is neat you should donate for it',
    shortdescription: 'neat prize. do donate',
    minimumbid: 10.0,
    sumdonations: false,
    startrun: 1,
    endrun: 1,
    starttime: null,
    endtime: null,
    provider: 'faulty',
    creator: 'ye',
    start_draw_time: run1.starttime?.toISO(),
    end_draw_time: run1.endtime?.toISO(),
  }),
);

const largestAllowedEstimate = ALLOWED_ESTIMATED_TIMES[ALLOWED_ESTIMATED_TIMES.length - 1];

describe('getPrizeRelativeAvailability', () => {
  it('shows as event-long without draw times', () => {
    const prize: Prize = {
      ...defaultPrize,
      start_draw_time: null,
      end_draw_time: null,
    };

    const availability = getPrizeRelativeAvailability(prize, now, [run1]);
    expect(availability).toEqual('Available all event long!');
  });

  it('shows as closed when past end draw time', () => {
    const prize: Prize = {
      ...defaultPrize,
      end_draw_time: now.minus(1000),
    };

    const availability = getPrizeRelativeAvailability(prize, now, [run1]);
    expect(availability).toEqual('No longer available for bidding.');
  });

  describe('with exact time bounds', () => {
    it('states opening time exactly when start time is near', () => {
      const startTime = now.plus(EXACT_TIME_RELATIVE_LIMIT - 1);
      const prize: Prize = {
        ...defaultPrize,
        starttime: startTime,
      };

      const startTimeExact = startTime.toLocaleString({
        hour: 'numeric',
        minute: '2-digit',
        timeZoneName: 'short',
      });

      const availability = getPrizeRelativeAvailability(prize, now, [run1]);
      expect(availability).toEqual(`Opens at ${startTimeExact}`);
    });

    it('states opening time as date when start time is far', () => {
      const startTime = now.plus({ days: 1, milliseconds: EXACT_TIME_RELATIVE_LIMIT });
      const prize: Prize = {
        ...defaultPrize,
        starttime: startTime,
      };

      const startTimeDate = startTime.toLocaleString(DateTime.DATE_MED);

      const availability = getPrizeRelativeAvailability(prize, now, [run1]);
      expect(availability).toEqual(`Opens at ${startTimeDate}`);
    });

    it('states closing time exactly when end time is near', () => {
      const startTime = now.minus(100);
      const endTime = now.plus(EXACT_TIME_RELATIVE_LIMIT);
      const prize: Prize = {
        ...defaultPrize,
        starttime: startTime,
        endtime: endTime,
      };

      const endTimeExact = endTime.toLocaleString({
        hour: 'numeric',
        minute: '2-digit',
        timeZoneName: 'short',
      });

      const availability = getPrizeRelativeAvailability(prize, now, [run1]);
      expect(availability).toEqual(`Open until ${endTimeExact}`);
    });

    it('states closing time as date when end time is far', () => {
      const startTime = now.minus(100);
      const endTime = now.plus({ days: 1, milliseconds: EXACT_TIME_RELATIVE_LIMIT });
      const prize: Prize = {
        ...defaultPrize,
        starttime: startTime,
        endtime: endTime,
      };

      const endTimeDate = endTime.toLocaleString(DateTime.DATE_MED);

      const availability = getPrizeRelativeAvailability(prize, now, [run1]);
      expect(availability).toEqual(`Open until ${endTimeDate}`);
    });
  });

  describe('with relative time bounds', () => {
    it('rounds time until closing within the maximum allowed', () => {
      const startDrawTime = now.minus(1);
      const endDrawTime = now.plus(largestAllowedEstimate.time - 1);
      const prize: Prize = {
        ...defaultPrize,
        startrun: null,
        endrun: null,
        start_draw_time: startDrawTime,
        end_draw_time: endDrawTime,
      };

      const availability = getPrizeRelativeAvailability(prize, now, [run1]);
      expect(availability).toEqual(`Closes ${largestAllowedEstimate.display}`);
    });

    it('shows only starting run name when estimated start is far', () => {
      const prize: Prize = {
        ...defaultPrize,
        start_draw_time: now.plus(largestAllowedEstimate.time + 1),
      };

      const availability = getPrizeRelativeAvailability(prize, now, [run1]);
      expect(availability).toEqual(`Opens when ${run1.name} \u2014 ${run1.category} starts`);
    });

    it('shows only ending run name when estimated end is far', () => {
      const prize: Prize = {
        ...defaultPrize,
        start_draw_time: now.minus(1),
        end_draw_time: now.plus(largestAllowedEstimate.time + 1),
      };

      const availability = getPrizeRelativeAvailability(prize, now, [run1]);
      expect(availability).toEqual(`Closes when ${run1.name} \u2014 ${run1.category} ends`);
    });

    it('shows run name and time when estimated start is near', () => {
      const prize: Prize = {
        ...defaultPrize,
        start_draw_time: now.plus(largestAllowedEstimate.time - 1),
      };

      const availability = getPrizeRelativeAvailability(prize, now, [run1]);
      expect(availability).toEqual(
        `Opens when ${run1.name} \u2014 ${run1.category} starts, ${largestAllowedEstimate.display}`,
      );
    });

    it('shows run name and time when estimated end is near', () => {
      const prize: Prize = {
        ...defaultPrize,
        start_draw_time: now.minus(1),
        end_draw_time: now.plus(largestAllowedEstimate.time - 1),
      };

      const availability = getPrizeRelativeAvailability(prize, now, [run1]);
      expect(availability).toEqual(
        `Closes when ${run1.name} \u2014 ${run1.category} ends, ${largestAllowedEstimate.display}`,
      );
    });
  });
});
