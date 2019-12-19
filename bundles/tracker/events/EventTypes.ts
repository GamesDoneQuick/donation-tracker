import { DateTime } from '../../public/util/TimeUtils';

export type Event = {
  id: string;
  short: string;
  name: string;
  canonicalUrl: string;
  public: string;
  useOneStepScreening: boolean;
  receiverName?: string;
  scheduleId?: string;
  startTime?: DateTime;
  timezone: string;
  locked: boolean;
  // Donations
  paypalEmail: string;
  paypalCurrency: string;
  targetAmount: number;
  allowDonations: boolean;
  minimumDonation: number;
  autoApproveThreshold?: number;
  // Prizes
  prizeCoordinator?: object; // User
  allowedPrizeCountries: Array<object>; // Array<Country>
  disallowedPrizeRegions: Array<object>; // Array<CountryRegion>
  prizeAcceptDeadlineDelta: number;
  // Statistics
  amount: number;
  count: number;
  max: number;
  avg?: number;
  // Emails
  donationEmailSender?: string;
  donationEmailTemplate?: string;
  pendingDonationEmailTemplate?: string;
  prizeContributorEmailTemplate?: string;
  prizeWinnerEmailTemplate?: string;
  prizeWinnerAcceptEmailTemplate?: string;
  prizeShippedEmailTemplate?: string;
};

export type EventSearchFilter = {
  id?: string;
  short?: string;
  name?: string;
  locked?: boolean;
  before?: DateTime;
  after?: DateTime;
};

export type EventAction =
  | { type: 'FETCH_EVENTS_STARTED' }
  | { type: 'FETCH_EVENTS_SUCCESS'; events: Array<Event> }
  | { type: 'FETCH_EVENTS_FAILED' }
  | { type: 'SELECT_EVENT'; eventId: number };
