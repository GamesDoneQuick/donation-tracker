import { APIEvent, PaginationInfo } from '@public/apiv2/APITypes';

import { Event } from '@tracker/events/EventTypes';

export function getFixtureEvent(overrides?: Partial<Event>): Event {
  return {
    id: '1',
    short: 'test',
    name: 'Test Event',
    canonicalUrl: '/testserver/tracker/events/1',
    public: 'Test Event',
    useOneStepScreening: false,
    timezone: 'America/New_York',
    locked: false,
    paypalEmail: 'paypal@example.com',
    paypalCurrency: 'USB',
    paypalImgurl: '',
    allowDonations: true,
    minimumDonation: 5,
    allowedPrizeCountries: [],
    disallowedPrizeRegions: [],
    prizeAcceptDeadlineDelta: 30,
    amount: 0,
    count: 0,
    max: 0,
    avg: 0,
    ...overrides,
  };
}

export function getFixturePagedEvent(overrides?: Partial<APIEvent>): PaginationInfo<APIEvent> {
  return {
    count: 1,
    previous: null,
    next: null,
    results: [
      {
        id: 1,
        type: 'event',
        short: 'test',
        name: 'Test Event',
        hashtag: '',
        datetime: '2024-01-01T11:30:00-05:00',
        timezone: 'America/New_York',
        receivername: 'Receiver',
        receiver_short: 'R',
        receiver_solicitation_text: 'Click here to receive emails from Receiver',
        receiver_logo: 'https://example.com/logo.png',
        receiver_privacy_policy: 'https://example.com/privacy/',
        paypalcurrency: 'USD',
        use_one_step_screening: true,
        allow_donations: true,
        locked: false,
        ...overrides,
      },
    ],
  };
}
