import { DateTime } from '@public/util/TimeUtils';

import { Run } from '@tracker/runs/RunTypes';

export type PrizeCategory = {
  name: string;
  public: string;
};

export type Prize = {
  id: string;
  name: string;
  public: string;
  description: string;
  shortDescription: string;
  /**
   * NOTE: This currently represents the server's idea of a canonical URL for
   * the prize, not this app's route for it.
   */
  canonicalUrl: string;
  extraInfo?: string;
  categoryId?: string;
  category?: PrizeCategory;
  /**
   * A representative image of the Prize, often as submitted by the prize donor.
   * Size and resolution can be variable.
   */
  image?: string;
  /**
   * A cropped image of the Prize, meant to fit consistently inside of stream layouts,
   * often taken specifically for the event.
   */
  altImage?: string;
  /**
   * An image for this prize that is hosted by the tracker itself in case remote
   * services for `image` or `altImage` aren't available.
   *
   * This will always take priority over the other two images.
   */
  imageFile?: string;
  estimatedValue?: number;
  minimumBid: number;
  maximumBid?: number;
  sumDonations: boolean;
  eventId: string;
  // When a prize's duration is bookmarked by runs, these are populated.
  // Prefer using `*DrawTime` when relative time information is needed.
  startRunId?: string;
  startRun?: Run;
  endRunId?: string;
  endRun?: Run;
  // When a prize's duration is manually specified, these are populated.
  // Prefer using `*DrawTime` when relative time information is needed.
  startTime?: DateTime;
  endTime?: DateTime;
  // These are "always" populated and are the real times a prize is open,
  // regardless of how the duration is determined, and updated according to the
  // current state of the schedule.
  startDrawTime?: DateTime;
  endDrawTime?: DateTime;
  provider?: string;
  creator?: string;
  creatorEmail?: string;
  creatorWebsite?: string;
  randomDraw: boolean;
  keyCode: boolean;
  handlerId?: string;
  requiresShipping: boolean;
  customCountryFilter: boolean;
  allowedPrizeCountries: string[];
  disallowedPrizeRegions: string[];
  numWinners: number;
  maxWinners: number;
  maxMultiWin: number;
};

export type PrizeSearchFilter = {
  id?: string;
  name?: string;
  // maps to `prize.eventId`
  event?: string;
  eventshort?: string;
};

export type PrizeAction =
  | { type: 'FETCH_PRIZES_STARTED' }
  | { type: 'FETCH_PRIZES_SUCCESS'; prizes: Prize[] }
  | { type: 'FETCH_PRIZES_FAILED' };
