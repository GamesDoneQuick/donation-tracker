import TimeUtils, { DateTime } from '@public/util/TimeUtils';

import { Run } from '@tracker/runs/RunTypes';

import getPrizeRelativeAvailability, {
  ALLOWED_ESTIMATED_TIMES,
  EXACT_TIME_RELATIVE_LIMIT,
} from '../getPrizeRelativeAvailability';
import { Prize } from '../PrizeTypes';

const now = TimeUtils.parseTimestamp('2019-12-10T10:00:00Z');

const run1: Run = {
  name: 'Spyro the Dragon',
  displayName: 'Spyro the Dragon',
  twitchName: 'Spyro the Dragon',
  deprecatedRunners: 'faulty',
  runners: [],
  console: 'PS1',
  commentators: '',
  description: 'Spyro a drago',
  startTime: TimeUtils.parseTimestamp('2019-12-10T09:00:00Z'),
  endTime: TimeUtils.parseTimestamp('2019-12-10T11:00:00Z'),
  order: 5,
  runTime: '1:40:00',
  setupTime: '0:05:00',
  coop: false,
  category: '120%',
  releaseYear: 1997,
  techNotes: '',
  public: 'Spyro the Dragon 120% (Big Event of the Year 2020)',
};

const defaultPrize: Prize = {
  id: '2',
  name: 'Some game codes with a long name',
  image: '/media/image.png',
  altImage: '/media/altimage.png',
  imageFile: '/media/imagefile.png',
  description: 'This prize is neat you should donate for it',
  shortDescription: 'neat prize. do donate',
  extraInfo: '',
  minimumBid: 10.0,
  maximumBid: 10.0,
  sumDonations: false,
  randomDraw: true,
  eventId: '1',
  startRunId: '1',
  endRunId: '1',
  startTime: undefined,
  endTime: undefined,
  maxWinners: 0,
  maxMultiWin: 1,
  provider: 'faulty',
  handlerId: '2',
  creator: 'ye',
  creatorEmail: 'idk@example.com',
  requiresShipping: true,
  customCountryFilter: true,
  keyCode: true,
  allowedPrizeCountries: ['40', '237'],
  disallowedPrizeRegions: [],
  startDrawTime: TimeUtils.parseTimestamp('2019-12-10T09:00:00Z'),
  endDrawTime: TimeUtils.parseTimestamp('2019-12-10T11:00:00Z'),
  canonicalUrl: 'http://localhost:8080/tracker/prize/2',
  public: 'Some game codes with a long name',
  numWinners: 0,
  startRun: run1,
  endRun: run1,
};

const largestAllowedEstimate = ALLOWED_ESTIMATED_TIMES[ALLOWED_ESTIMATED_TIMES.length - 1];

describe('getPrizeRelativeAvailability', () => {
  it('shows as event-long without draw times', () => {
    const prize: Prize = {
      ...defaultPrize,
      startDrawTime: undefined,
      endDrawTime: undefined,
    };

    const availability = getPrizeRelativeAvailability(prize, now);
    expect(availability).toEqual('Available all event long!');
  });

  it('shows as event-long without start draw time', () => {
    const prize: Prize = {
      ...defaultPrize,
      startDrawTime: undefined,
    };

    const availability = getPrizeRelativeAvailability(prize, now);
    expect(availability).toEqual('Available all event long!');
  });

  it('shows as event-long without end draw time', () => {
    const prize: Prize = {
      ...defaultPrize,
      endDrawTime: undefined,
    };

    const availability = getPrizeRelativeAvailability(prize, now);
    expect(availability).toEqual('Available all event long!');
  });

  it('shows as closed when past end draw time', () => {
    const prize: Prize = {
      ...defaultPrize,
      endDrawTime: now.minus(1000),
    };

    const availability = getPrizeRelativeAvailability(prize, now);
    expect(availability).toEqual('No longer available for bidding.');
  });

  describe('with exact time bounds', () => {
    it('states opening time exactly when start time is near', () => {
      const startTime = now.plus(EXACT_TIME_RELATIVE_LIMIT - 1);
      const prize: Prize = {
        ...defaultPrize,
        startTime,
      };

      const startTimeExact = startTime.toLocaleString({
        hour: 'numeric',
        minute: '2-digit',
        timeZoneName: 'short',
      });

      const availability = getPrizeRelativeAvailability(prize, now);
      expect(availability).toEqual(`Opens at ${startTimeExact}`);
    });

    it('states opening time as date when start time is far', () => {
      const startTime = now.plus({ days: 1, milliseconds: EXACT_TIME_RELATIVE_LIMIT });
      const prize: Prize = {
        ...defaultPrize,
        startTime,
      };

      const startTimeDate = startTime.toLocaleString(DateTime.DATE_MED);

      const availability = getPrizeRelativeAvailability(prize, now);
      expect(availability).toEqual(`Opens at ${startTimeDate}`);
    });

    it('states closing time exactly when end time is near', () => {
      const startTime = now.minus(100);
      const endTime = now.plus(EXACT_TIME_RELATIVE_LIMIT);
      const prize: Prize = {
        ...defaultPrize,
        startTime,
        endTime,
      };

      const endTimeExact = endTime.toLocaleString({
        hour: 'numeric',
        minute: '2-digit',
        timeZoneName: 'short',
      });

      const availability = getPrizeRelativeAvailability(prize, now);
      expect(availability).toEqual(`Open until ${endTimeExact}`);
    });

    it('states closing time as date when end time is far', () => {
      const startTime = now.minus(100);
      const endTime = now.plus({ days: 1, milliseconds: EXACT_TIME_RELATIVE_LIMIT });
      const prize: Prize = {
        ...defaultPrize,
        startTime,
        endTime,
      };

      const endTimeDate = endTime.toLocaleString(DateTime.DATE_MED);

      const availability = getPrizeRelativeAvailability(prize, now);
      expect(availability).toEqual(`Open until ${endTimeDate}`);
    });
  });

  describe('with relative time bounds', () => {
    it('rounds time until opening within the maximum allowed', () => {
      const startDrawTime = now.plus(largestAllowedEstimate.time - 1);
      const prize: Prize = {
        ...defaultPrize,
        startRun: undefined,
        startDrawTime,
      };

      const availability = getPrizeRelativeAvailability(prize, now);
      expect(availability).toEqual(`Opens ${largestAllowedEstimate.display}`);
    });

    it('rounds time until closing within the maximum allowed', () => {
      const startDrawTime = now.minus(1);
      const endDrawTime = now.plus(largestAllowedEstimate.time - 1);
      const prize: Prize = {
        ...defaultPrize,
        startRun: undefined,
        endRun: undefined,
        startDrawTime,
        endDrawTime,
      };

      const availability = getPrizeRelativeAvailability(prize, now);
      expect(availability).toEqual(`Closes ${largestAllowedEstimate.display}`);
    });

    it('shows only starting run name when estimated start is far', () => {
      const prize: Prize = {
        ...defaultPrize,
        startDrawTime: now.plus(largestAllowedEstimate.time + 1),
        startRun: {
          ...run1,
          startTime: now.plus(largestAllowedEstimate.time + 1),
        },
      };

      const availability = getPrizeRelativeAvailability(prize, now);
      expect(availability).toEqual(`Opens when ${run1.name} \u2014 ${run1.category} starts`);
    });

    it('shows only ending run name when estimated end is far', () => {
      const prize: Prize = {
        ...defaultPrize,
        startDrawTime: now.minus(1),
        endDrawTime: now.plus(largestAllowedEstimate.time + 1),
        endRun: {
          ...run1,
          endTime: now.plus(largestAllowedEstimate.time + 1),
        },
      };

      const availability = getPrizeRelativeAvailability(prize, now);
      expect(availability).toEqual(`Closes when ${run1.name} \u2014 ${run1.category} ends`);
    });

    it('shows run name and time when estimated start is near', () => {
      const prize: Prize = {
        ...defaultPrize,
        startDrawTime: now.plus(largestAllowedEstimate.time - 1),
        startRun: {
          ...run1,
          startTime: now.plus(largestAllowedEstimate.time - 1),
        },
      };

      const availability = getPrizeRelativeAvailability(prize, now);
      expect(availability).toEqual(
        `Opens when ${run1.name} \u2014 ${run1.category} starts, ${largestAllowedEstimate.display}`,
      );
    });

    it('shows run name and time when estimated end is near', () => {
      const prize: Prize = {
        ...defaultPrize,
        startDrawTime: now.minus(1),
        endDrawTime: now.plus(largestAllowedEstimate.time - 1),
        endRun: {
          ...run1,
          endTime: now.plus(largestAllowedEstimate.time - 1),
        },
      };

      const availability = getPrizeRelativeAvailability(prize, now);
      expect(availability).toEqual(
        `Closes when ${run1.name} \u2014 ${run1.category} ends, ${largestAllowedEstimate.display}`,
      );
    });
  });
});
